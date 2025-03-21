import boto3
import datetime
import pandas as pd
from tabulate import tabulate
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import logging
import io

#! Configure logging for Lambda
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_rds_metrics_report():
    """
    Generate a report for RDS instances with the following metrics:
    - RDS Instance Name
    - Instance State
    - Allocated Space
    - Free Storage Space (latest)
    - Free Storage Space Percentage
    - Freeable Memory (latest)
    """
    rds_client = boto3.client("rds")
    cloudwatch = boto3.client("cloudwatch")
    end_time = datetime.datetime.utcnow()  # get time
    instances = rds_client.describe_db_instances()  # get list of instances
    results = []

    for instance in instances["DBInstances"]:
        instance_id = instance["DBInstanceIdentifier"]
        allocated_storage_gb = instance["AllocatedStorage"]
        instance_state = instance["DBInstanceStatus"]

        #! Free storage space value
        free_storage_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/RDS",
            MetricName="FreeStorageSpace",
            Dimensions=[{"Name": "DBInstanceIdentifier", "Value": instance_id},],
            StartTime=end_time - datetime.timedelta(hours=1),
            EndTime=end_time,
            Period=300,  # 5-minute
            Statistics=["Average"],
        )

        #! freeable memory metric value
        freeable_memory_response = cloudwatch.get_metric_statistics(
            Namespace="AWS/RDS",
            MetricName="FreeableMemory",
            Dimensions=[
                {"Name": "DBInstanceIdentifier", "Value": instance_id},
            ],
            StartTime=end_time - datetime.timedelta(hours=1),
            EndTime=end_time,
            Period=300,  # // 5-minute periods
            Statistics=["Average"],
        )

        #! Extract the latest free storage space (in bytes, convert to GB)
        free_storage_gb = 0
        if free_storage_response["Datapoints"]:
            latest_point = max(
                free_storage_response["Datapoints"], key=lambda x: x["Timestamp"]
            )
            free_storage_gb = round(latest_point["Average"] / (1024 * 1024 * 1024), 2)

        #! Calculate free storage percentage
        free_storage_percent = (
            round((free_storage_gb / allocated_storage_gb) * 100, 2)
            if allocated_storage_gb > 0
            else 0
        )

        #! Extract the latest freeable memory (in bytes, convert to GB)

        freeable_memory_gb = 0
        if freeable_memory_response["Datapoints"]:
            latest_point = max(
                freeable_memory_response["Datapoints"], key=lambda x: x["Timestamp"]
            )
            freeable_memory_gb = round(
                latest_point["Average"] / (1024 * 1024 * 1024), 2
            )

        results.append(
            {
                "RDS Instance Name": instance_id,
                "Instance State": instance_state,
                "Allocated Space (GB)": allocated_storage_gb,
                "Free Storage Space (GB)": free_storage_gb,
                "Free Storage Space (%)": free_storage_percent,
                "Freeable Memory (GB)": freeable_memory_gb,
            }
        )

    return results


def send_report_email(df, csv_data, recipients):
    """Send the report via AWS SES"""
    try:
        #! Create SES client
        ses_client = boto3.client("ses")

        #! Create message container
        msg = MIMEMultipart()
        msg["Subject"] = (
            f'Weekly RDS Metrics Report - {datetime.datetime.now().strftime("%Y-%m-%d")}'
        )
        msg["From"] = "admin01@readywire.com"  # Must be verified in SES
        msg["To"] = ", ".join(recipients)

        # Format the numeric columns first
        formatted_df = df.copy()
        numeric_columns = ["Allocated Space (GB)", "Free Storage Space (GB)", 
                          "Free Storage Space (%)", "Freeable Memory (GB)"]
        
        for col in numeric_columns:
            formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2f}")

        #! Convert DataFrame to HTML with color highlighting
        def highlight_storage_percent(row):
            # Convert the string back to float for comparison
            free_percent = float(row["Free Storage Space (%)"])
            if free_percent < 15:
                return ["", "", "", "", "background-color: red", ""]
            elif free_percent < 20:
                return ["", "", "", "", "background-color: orange", ""]
            else:
                return ["", "", "", "", "", ""]
        
        styled_df = formatted_df.style.apply(highlight_storage_percent, axis=1)
        html_table = styled_df.to_html(index=False)

        html_content = f"""
        <html>
        <head>
            <style>
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h2>RDS Metrics Report - {datetime.datetime.now().strftime("%Y-%m-%d")}</h2>
            {html_table}
            <p>This is an automated report. Please find the CSV attachment for your records.</p>
            <p><strong>Note:</strong> Red cells indicate free storage space less than 15%, orange cells indicate less than 20%.</p>
        </body>
        </html>
        """

        # // Attach HTML content
        part = MIMEText(html_content, "html")
        msg.attach(part)

        # // Attach CSV file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"rds_metrics_report_{timestamp}.csv"

        part = MIMEApplication(csv_data)
        part.add_header("Content-Disposition", "attachment", filename=csv_filename)
        msg.attach(part)

        # // Send email
        response = ses_client.send_raw_email(
            Source=msg["From"],
            Destinations=recipients,
            RawMessage={"Data": msg.as_string()},
        )

        logger.info(f"Email sent successfully! Message ID: {response['MessageId']}")
        return True

    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False


def lambda_handler(event, context):
    """Lambda function handler"""
    try:
        #! Default recipients from environment variable or override with event parameters
        recipients = os.environ.get(
            "EMAIL_RECIPIENTS", "saasadmin@readywire.com"
        ).split(",")

        #! Allow overriding recipients from the event
        if event and "recipients" in event:
            recipients = event["recipients"]

        #! Get metrics data
        rds_metrics = get_rds_metrics_report()

        if not rds_metrics:
            logger.warning("No RDS instances found in the account.")
            return {"statusCode": 200, "body": "No RDS instances found in the account."}

        df = pd.DataFrame(rds_metrics)

        #! Create CSV in memory instead of writing to disk
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue().encode()

        #! Send email
        email_sent = send_report_email(df, csv_data, recipients)

        return {
            "statusCode": 200,
            "body": f'RDS metrics report generated and {"email sent successfully" if email_sent else "failed to send email"}.',
        }

    except Exception as e:
        error_message = f"Error in lambda_handler: {str(e)}"
        logger.error(error_message)
        return {"statusCode": 500, "body": error_message}


# ? For local testing
if __name__ == "__main__":
    lambda_handler(None, None)
  
