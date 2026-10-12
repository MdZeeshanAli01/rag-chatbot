# Cloud Computing Mini-Project: Cloud-Native RAG Chatbot on AWS

**Course:** Cloud Computing (CC)  
**Project Title:** Serverless & Containerized Retrieval-Augmented Generation (RAG) Document Assistant  
**Cloud Service Provider:** Amazon Web Services (AWS)  

---

## 🏛️ 1. System Architecture Overview

```
                                  [ End User / Browser ]
                                             │
                                      HTTPS (Port 443)
                                             ▼
                             [ Amazon CloudFront (CDN) ]
                              │                       │
                Static Assets │                       │ API Requests (/upload, /ask)
                              ▼                       ▼
                     [ Amazon S3 Bucket ]     [ Amazon API Gateway ]
                     (Frontend Web Hosting)           │
                                                      ▼
                                            [ AWS Lambda / ECS Fargate ]
                                            (FastAPI Backend Container)
                                             │       │          │
                 ┌───────────────────────────┘       │          └──────────────────────────┐
                 ▼                                   ▼                                     ▼
        [ Amazon S3 Bucket ]            [ Amazon Bedrock ]                      [ Amazon OpenSearch Serverless ]
       (Raw Document Storage)         (Titan / Claude / Llama)                   (Vector Store & Similarity Search)
                                       Embeddings & Text Gen                     (or Amazon Bedrock Knowledge Bases)
                                                     │
                                                     ▼
                                        [ AWS Secrets Manager / IAM ]
                                           (Least-Privilege Security)
```

---

## 📊 2. AWS Services Mapping & Rationale Table

This table directly answers the submission requirement: **Why was each service selected over alternatives?**

| AWS Service | Role in Project | Why This Service? (Technical Justification) | Alternatives Considered & Why Rejected |
|---|---|---|---|
| **Amazon S3 (Simple Storage Service)** | 1. Hosting Static Frontend (HTML, CSS, JS)<br>2. Object store for uploaded PDF documents | - 99.999999999% (11 9's) data durability.<br>- Native static website hosting capabilities.<br>- Highly cost-effective pay-per-GB model with no idle server cost. | **Amazon EBS**: Block storage tied to a single EC2 instance; cannot scale globally or host static websites natively without a running web server. |
| **Amazon CloudFront** | Content Delivery Network (CDN) & SSL Termination | - Global edge caching reduces frontend latency to single-digit milliseconds.<br>- Enforces secure HTTPS with free AWS Certificate Manager (ACM) SSL certificates.<br>- Single domain routing for both S3 frontend and API Gateway backend (eliminates CORS issues). | **Direct S3 Public Access**: Exposes bucket publicly, lacks edge caching, and doesn't provide custom SSL certificates. |
| **AWS Lambda** or **Amazon ECS (Fargate)** | Backend Compute Execution (FastAPI Server / Container) | - **Serverless Execution**: Scales from zero to thousands of concurrent requests.<br>- Zero cost when idle (crucial for student project budgets).<br>- Automated high availability and zero OS patching/maintenance overhead. | **Amazon EC2 (Virtual Machines)**: Requires manual OS patching, security hardening, load balancing configuration, and incurs charges 24/7 even when idle. |
| **Amazon API Gateway** | API Management & Request Routing | - Fully managed REST/HTTP API endpoint.<br>- Built-in throttling, DDoS defense, authentication, request validation, and CORS handling.<br>- Seamless integration with Lambda and CloudFront. | **Self-hosted Nginx on EC2**: Requires managing and scaling server instances manually. |
| **Amazon Bedrock** | Foundation Models for Embeddings & LLM Generation | - Native, enterprise-grade serverless GenAI service.<br>- Direct access to state-of-the-art models (Anthropic Claude 3.5 Sonnet, Amazon Titan Embeddings, Meta Llama 3) via simple API calls.<br>- Data privacy: Customer data is never used to train base models. | **Self-hosted HuggingFace models on EC2 GPU (e.g. g4dn/g5)**: High hourly cost ($0.50–$3.00/hr) with idle billing, complex CUDA driver setups, and scaling bottlenecks. |
| **Amazon OpenSearch Serverless** / **Bedrock Knowledge Bases** | Vector Database for RAG Semantic Search | - Native vector engine supporting k-Nearest Neighbor (k-NN) search.<br>- Automatically indexes dense vector embeddings generated from document chunks.<br>- Fully managed serverless cluster scaling on demand. | **Self-hosted FAISS on EC2**: In-memory only; loses index on server restart or auto-scaling events, requiring custom persistence logic. |
| **AWS Identity and Access Management (IAM)** | Security & Access Governance | - Role-based least-privilege security model.<br>- Uses temporary STS credentials rather than long-lived API keys.<br>- Seamless authorization between Lambda, S3, Bedrock, and OpenSearch. | **Hardcoded API Keys / Secrets**: Dangerous vulnerability leading to credential leakage and AWS account compromise. |
| **AWS CloudWatch** | Monitoring, Logging & Observability | - Automatically collects stdout/stderr logs from FastAPI and Lambda.<br>- Metrics for API latency, 4xx/5xx error rates, and Bedrock invocation token usage.<br>- Configurable alarms for threshold breaches. | **Self-hosted ELK Stack**: High operational burden and resource requirements for a mini project. |

---

## 🛠️ 3. Two Deployment Implementation Paths

Depending on your submission requirements, you have two approaches:

### Path A: Modern Serverless Architecture (Maximum Marks for Cloud Architecture)
- **Frontend**: Amazon S3 + CloudFront
- **API**: Amazon API Gateway + AWS Lambda (FastAPI with Mangum adapter)
- **AI / LLM**: Amazon Bedrock (`amazon.titan-embed-text-v2:0` + `anthropic.claude-3-5-sonnet` or `meta.llama3-70b-instruct`)
- **Storage**: Amazon S3 (PDF uploads)

### Path B: Containerized Docker on AWS EC2 (Easiest to deploy in < 15 mins)
- An **AWS EC2 (t3.micro / t3.small)** instance.
- **Docker & Docker-Compose** running FastAPI + Frontend.
- **Amazon S3** for persistent PDF storage.
- **IAM Role** attached to EC2 for secure AWS access.

---

## 🚀 4. Step-by-Step Deployment: Path B (EC2 Containerized - Recommended for Quick Submission)

### Step 1: Launch an EC2 Instance on AWS
1. Go to AWS Console $\rightarrow$ **EC2** $\rightarrow$ **Launch Instance**.
2. **Name:** `rag-chatbot-server`
3. **AMI:** Ubuntu Server 24.04 LTS (HVM), SSD Volume Type.
4. **Instance Type:** `t3.small` (2 vCPU, 2GB RAM - recommended for running embeddings) or `t3.micro` (Free Tier).
5. **Key Pair:** Create or select an existing `.pem` key pair.
6. **Network Settings (Security Group):**
   - Allow **SSH (Port 22)** from `My IP`.
   - Allow **HTTP (Port 80)** from `0.0.0.0/0` (Anywhere).
   - Allow **Custom TCP (Port 8000)** from `0.0.0.0/0`.
7. **Storage:** 20 GiB gp3.
8. Click **Launch Instance**.

---

### Step 2: Attach IAM Role to EC2 (No Hardcoded Secrets!)
1. Go to **IAM Console** $\rightarrow$ **Roles** $\rightarrow$ **Create Role**.
2. Choose **AWS service** $\rightarrow$ **EC2**.
3. Attach policies:
   - `AmazonS3FullAccess` (or scoped to your bucket).
   - `AmazonBedrockFullAccess` (if using Bedrock models).
4. Name the role: `RAGChatbotEC2Role`.
5. In EC2 Console: Select your instance $\rightarrow$ **Actions** $\rightarrow$ **Security** $\rightarrow$ **Modify IAM role** $\rightarrow$ Attach `RAGChatbotEC2Role`.

---

### Step 3: Connect to EC2 and Configure Environment
Open your local terminal and SSH into the instance:

```bash
ssh -i "your-key.pem" ubuntu@<YOUR-EC2-PUBLIC-IP>
```

Update system and install Python + Docker + Git:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git docker.io docker-compose
sudo usermod -aG docker ubuntu
```

---

### Step 4: Clone Repository & Setup Project
```bash
git clone https://github.com/MdZeeshanAli01/rag-chatbot.git
cd rag-chatbot/backend
```

Create `.env` file with your credentials:
```bash
nano .env
```
Paste your settings:
```ini
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
PORT=8000
```
Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

---

### Step 5: Run with Systemd Service (Production Background Daemon)
Create a systemd service file so the chatbot auto-starts on boot:

```bash
sudo nano /etc/systemd/system/rag-chatbot.service
```

Paste the following configuration:

```ini
[Unit]
Description=FastAPI RAG Chatbot Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/rag-chatbot/backend
EnvironmentFile=/home/ubuntu/rag-chatbot/backend/.env
ExecStart=/usr/bin/python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rag-chatbot
sudo systemctl start rag-chatbot
```

Check status:
```bash
sudo systemctl status rag-chatbot
```

---

### Step 6: Access Your Live AWS Application
Open your browser and navigate to:
👉 `http://<YOUR-EC2-PUBLIC-IP>:8000/`

You will see the complete chatbot web interface running live on Amazon Web Services!

---

## 🎤 5. Cloud Computing Viva / Presentation Q&A Defense Guide

### Q1: What makes this architecture "Cloud-Native"?
> **Answer:** "A traditional application relies on a monolithic local environment where storage, compute, and model inference are tightly coupled. In this AWS architecture, compute is decoupled from storage: documents are stored on Amazon S3 with high durability, compute is stateless (FastAPI on EC2/Fargate/Lambda), and AI inference is delegated to managed foundation models via Amazon Bedrock/API providers. This allows each component to scale independently based on demand."

### Q2: Why did you choose Amazon S3 over Amazon EBS for document storage?
> **Answer:** "Amazon Elastic Block Store (EBS) is block storage tied to a single EC2 instance within an Availability Zone. If that instance fails, access is severed. Amazon S3 is object storage that automatically distributes data across a minimum of three Availability Zones, offering 99.999999999% durability and HTTP/REST API accessibility from any microservice without consuming instance disk space."

### Q3: How does this architecture handle security and secret management?
> **Answer:** "Instead of hardcoding API keys or committing secrets to version control, we follow the principle of least privilege. We use IAM Roles for Amazon EC2 / AWS Lambda, allowing temporary credential generation via AWS Security Token Service (STS). Environment variables are managed via AWS Systems Manager Parameter Store or Secrets Manager."

### Q4: How does RAG reduce cloud computing costs compared to fine-tuning?
> **Answer:** "Fine-tuning requires provisioning expensive GPU instances (such as AWS p4d/p5 instances with NVIDIA A100/H100 chips) for days, incurring thousands of dollars in training costs. RAG decouples knowledge from weights: we chunk and store domain documents as inexpensive vector embeddings in a vector database, retrieving only top-k relevant snippets at inference time. This dramatically reduces cost, eliminates retraining latency, and prevents LLM hallucinations."
