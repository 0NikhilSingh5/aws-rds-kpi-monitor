# 📌 RDS Metrics Monitoring and Reporting Lambda

## 📖 Overview
This AWS Lambda function generates a **weekly RDS Metrics Report** that includes vital information about your RDS instances, such as:

- **Instance Name**
- **Instance State**
- **Allocated Storage**
- **Free Storage Space** (latest)
- **Free Storage Percentage**
- **Freeable Memory** (latest)

The report is formatted into an **HTML table with color-coded highlights** for storage thresholds and sent via **AWS SES (Simple Email Service)** to specified recipients.

---
## 🚀 Features
✅ **Automated RDS Metrics Collection** – Uses AWS CloudWatch to gather storage and memory metrics.

✅ **Data Formatting & Highlighting** – Applies conditional formatting to flag critical storage levels.

✅ **Email Notification** – Sends the report with an **HTML summary** and a **CSV attachment**.

✅ **Flexible Configuration** – Recipients can be set via environment variables or passed in the Lambda event.

✅ **Efficient Data Handling** – Uses in-memory CSV processing instead of file system operations.

---
## 📂 Project Structure
```
📁 RDS-Metrics-Report-Lambda
│── lambda_function.py        # Main Lambda function script
│── README.md                 # Project documentation
│── requirements.txt          # Python dependencies
```

---
## ⚙️ Prerequisites
### 🛠 AWS Services Used:
- **AWS Lambda** (to run the function)
- **AWS RDS** (to monitor database instances)
- **AWS CloudWatch** (to fetch RDS metrics)
- **AWS SES** (to send email reports)

### 📌 Required IAM Permissions:
Ensure your Lambda function has a role with the following permissions:
```json
{
  "Effect": "Allow",
  "Action": [
    "rds:DescribeDBInstances",
    "cloudwatch:GetMetricStatistics",
    "ses:SendRawEmail"
  ],
  "Resource": "*"
}
```
---
## 🛠 Setup Instructions
### 1️⃣ **Deploy to AWS Lambda**
- Create a **Lambda function** in AWS.
- Upload the **Python script** (`lambda_function.py`).
- Configure the **Execution Role** with necessary permissions.

### 2️⃣ **Set Environment Variables**
```sh
EMAIL_RECIPIENTS="admin@yourdomain.com,user@yourdomain.com"
```

### 3️⃣ **Schedule the Lambda Execution**
To automate the weekly report, set up an AWS **EventBridge (CloudWatch) Rule**:
- Go to **EventBridge** → **Rules**
- Create a **new rule** with a **Cron Expression**
- Example for **every Monday at 8 AM UTC**:
  ```sh
  cron(0 8 ? * MON *)
  ```
- Choose the **target** as your Lambda function.

---
## 📧 Email Report Example
### ✅ **HTML Email Preview**
📌 **Critical Storage Levels are Highlighted:**

| RDS Instance | Allocated Space (GB) | Free Storage (GB) | Free Storage (%) | Freeable Memory (GB) |
|-------------|------------------|------------------|----------------|----------------|
| db-instance-1 | 50 | 7 | 🔴 14% | 1.2 |
| db-instance-2 | 100 | 18 | 🟠 18% | 2.4 |
| db-instance-3 | 200 | 45 | ✅ 22% | 3.1 |

🔴 **Red**: Free storage < 15%  
🟠 **Orange**: Free storage < 20%  
✅ **Green**: Healthy

---
## 🛠 Local Testing
If you want to test the function locally, install dependencies and run the script:
```sh
pip install -r requirements.txt
python lambda_function.py
```

---
## 🤝 Contributions
Feel free to contribute by submitting pull requests or reporting issues!

---
## 📜 License
This project is licensed under the **MIT License**.

---
## 🔗 Useful Links
- 📖 [AWS Lambda Docs](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)
- 📊 [AWS CloudWatch Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/working-with-metrics.html)
- ✉️ [AWS SES Docs](https://docs.aws.amazon.com/ses/latest/dg/Welcome.html)

🚀 **Happy Monitoring!** 🚀

