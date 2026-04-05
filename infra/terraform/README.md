# AWS Infrastructure — Terraform

Infrastructure-as-Code for the Agent-Based Hiring System, provisioning EKS (with Fargate), ECR, RDS PostgreSQL, and networking on AWS.

---

## File Inventory

```
infra/terraform/
├── versions.tf              # Terraform & AWS provider version pins
├── variables.tf             # All input variables with defaults
├── terraform.tfvars.example # Example values (copy to terraform.tfvars)
├── vpc.tf                   # VPC, subnets, IGW, NAT Gateway, routes
├── ecr.tf                   # ECR repos (7) with scan-on-push & lifecycle
├── eks.tf                   # EKS cluster (K8s 1.32) + managed node group
├── eks-fargate.tf           # Fargate profiles (services + kube-system)
├── rds.tf                   # RDS PostgreSQL 15
├── iam.tf                   # IAM roles (cluster, nodes, Fargate, OIDC)
├── outputs.tf               # Exported endpoints, URLs, and helper commands
└── k8s/
    ├── namespaces.yaml                      # frontend + services namespaces
    ├── frontend-deployment.yaml             # React/nginx, 2 replicas, LB, Port 80 (Auto-managed by CI/CD)
    ├── coordinator-agent-deployment.yaml    # Fargate, HPA 1→5
    ├── resume-intake-agent-deployment.yaml  # Fargate, HPA 1→5
    ├── screening-agent-deployment.yaml      # Fargate, HPA 1→5
    ├── audit-agent-deployment.yaml          # Fargate, HPA 1→5
    ├── ranking-agent-deployment.yaml        # Fargate, HPA 1→5
    ├── skill-assessment-agent-deployment.yaml # Fargate, HPA 1→5
    └── secrets.yaml.example                 # Template for credentials

.github/workflows/
├── terraform.yml            # TF Plan/Apply & K8s Deploy (Push/Manual dispatch)
├── terraform-manage.yml     # Cost optimization targeted destroy/recreate (Manual)
├── deploy-db.yml            # SQL schema & migrations (automatic upon push to db/)
├── deploy-services.yml      # CI/CD for Python Agents to ECR & K8s
├── frontend-build.yml       # Reusable GHCR frontend build workflow
├── deploy-frontend.yml      # CI/CD for Frontend React app to ECR & K8s
└── build.yml                # Core reusable service image build/push workflow
```

---

## Architecture

```mermaid
graph TB
    Internet((Internet))

    subgraph VPC["VPC — 10.0.0.0/16"]
        subgraph PubSub["Public Subnets (10.0.1.0/24, 10.0.2.0/24)"]
            IGW[Internet Gateway]
            ALB[Application Load Balancer]
            NAT[NAT Gateway]
        end

        subgraph PrivSub["Private Subnets (10.0.10.0/24, 10.0.11.0/24)"]
            subgraph EKS["EKS Cluster — Kubernetes 1.32"]
                subgraph NodeGroup["Managed Node Group (t3.small)"]
                    FE["frontend<br/>namespace<br/>(2 replicas)"]
                end
                subgraph Fargate["Fargate — Serverless"]
                    COORD["coordinator-agent"]
                    RESUME["resume-intake-agent"]
                    SCREEN["screening-agent"]
                    AUDIT["audit-agent"]
                    RANKING["ranking-agent"]
                    SKILL["skill-assessment-agent"]
                end
            end
            RDS[("RDS PostgreSQL 15<br/>db.t3.micro<br/>Encrypted")]
        end
    end

    ECR["ECR<br/>(7 repositories)"]

    Internet --> IGW --> ALB --> FE
    COORD --> RDS
    COORD <--> RESUME
    COORD <--> SCREEN
    COORD <--> AUDIT
    COORD <--> RANKING
    COORD <--> SKILL
    PrivSub --> NAT --> IGW
    EKS -.-> ECR
```

| Component | Details |
|-----------|---------|
| **VPC** | `10.0.0.0/16`, 2 AZs (`ap-southeast-1a`, `1b`), single NAT (cost-optimized) |
| **EKS** | K8s 1.32, public+private endpoint, API/audit/authenticator logging. Root & all IAM users granted ClusterAdmin via Access Entries. |
| **Node Group** | `t3.small`, 1–4 nodes (managed node group), hosts the `frontend` namespace. |
| **Fargate** | `services` namespace — coordinator, resume-intake, screening, skill-assessment, audit, and ranking agents |
| **RDS** | PostgreSQL 15, gp2 storage (20 GB), 0-day backups (Free Tier) |
| **ECR** | 7 repos, immutable tags, scan-on-push, 10-image lifecycle cleanup |
| **Security** | Node security groups configured with NodePort ingress (30000-32767) for ELB health checks. |

---

## Prerequisites & Credentials

### Required Before `terraform apply`

| # | Item | How to Set Up |
|---|------|---------------|
| 1 | **AWS CLI & Credentials** | `aws configure` or set `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`. Verify: `aws sts get-caller-identity` |
| 2 | **IAM Permissions** | Setup IAM policy based on **Option 1 or Option 2 below** |
| 3 | **Terraform ≥ 1.5** | Verify: `terraform --version` |
| 4 | **Database Password** | Set a strong password in `terraform.tfvars` (see Files to Update below) |
| 5 | **GitHub Secrets** (for CI/CD) | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `TF_VAR_DB_PASSWORD` |

---

### IAM Permissions Setup (For CI/CD & Local Deploy)

#### Option 1: Minimum Privilege Custom Policy (Recommended)

Create an IAM policy with this exact JSON and attach it:

<details>
<summary>Click to show IAM JSON Policy</summary>

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*Vpc*", "ec2:*Subnet*", "ec2:*InternetGateway*", "ec2:*NatGateway*",
        "ec2:*Address*", "ec2:*Route*", "ec2:*SecurityGroup*", "ec2:*Tags*",
        "ec2:DescribeAvailabilityZones", "ec2:DescribeAccountAttributes", "ec2:DescribeNetworkInterfaces"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "eks:CreateCluster", "eks:DeleteCluster", "eks:DescribeCluster", "eks:UpdateCluster*",
        "eks:CreateNodegroup", "eks:DeleteNodegroup", "eks:DescribeNodegroup", "eks:UpdateNodegroup*",
        "eks:CreateFargateProfile", "eks:DeleteFargateProfile", "eks:DescribeFargateProfile",
        "eks:*Tag*", "eks:List*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:*Repository*", "ecr:*LifecyclePolicy*", "ecr:PutImageScanningConfiguration", "ecr:*Tag*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:*DBInstance*", "rds:*DBSubnetGroup*", "rds:*Tag*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:*Role*", "iam:PassRole", "iam:*OpenIDConnectProvider*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket", "s3:ListBucket", "s3:GetBucketVersioning", "s3:PutBucketVersioning",
        "s3:GetObject", "s3:PutObject", "s3:DeleteObject"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:DeleteItem", "dynamodb:DescribeTable", "dynamodb:CreateTable"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:*LogGroup*", "sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}
```
</details>

#### Option 2: AWS Managed Policies + Custom EKS Policy (Quick Setup)

Attach these **managed policies** to the IAM user/role:
- `AmazonVPCFullAccess`
- `AmazonEC2FullAccess`
- `AmazonEC2ContainerRegistryFullAccess`
- `AmazonRDSFullAccess`
- `IAMFullAccess`
- `CloudWatchLogsFullAccess`
- `AmazonS3FullAccess`
- `AmazonDynamoDBFullAccess`

Then add a **custom inline policy** named `EKS-FullAccess` (AWS has no managed policy for EKS user-level management):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "eks:*", "Resource": "*" }
  ]
}
```

> ⚠️ Option 2 grants broader permissions than needed. Use **Option 1** for production.

### Required After `terraform apply`

| # | Item | How to Set Up |
|---|------|---------------|
| 5 | **kubectl** | Install from [kubernetes.io](https://kubernetes.io/docs/tasks/tools/). Configure: `aws eks update-kubeconfig --name hiring-system-dev --region ap-southeast-1` |
| 6 | **OpenAI API Key** | Needed for K8s secrets — base64 encode: `echo -n "sk-..." \| base64` |
| 7 | **RDS Hostname** | Auto-output by Terraform after apply — copy into K8s secrets |

---

## Files to Update

### 1. `terraform.tfvars` (create from example)

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:

```hcl
db_password = "YOUR_STRONG_PASSWORD_HERE"  # ⚠️ Required — replace before apply

# Optional overrides (defaults are already set):
# aws_region         = "ap-southeast-1"
# node_instance_type = "t3.micro"
# db_instance_class  = "db.t3.micro"
```

### 2. `k8s/secrets.yaml` (create from example, post-apply)

```bash
cp k8s/secrets.yaml.example k8s/secrets.yaml
```

Edit `k8s/secrets.yaml` and replace `<BASE64_ENCODED_VALUE>` placeholders:

```bash
echo -n "sk-your-openai-key" | base64               # → openai-api-key
echo -n "your-rds-hostname.rds.amazonaws.com" | base64  # → db-host  (from terraform output)
echo -n "dbadmin" | base64                           # → db-username
echo -n "your-db-password" | base64                  # → db-password
```

### 3. CI/CD Placeholder Automation (NO Manual Edits Required)

Unlike traditional setups, the repository is configured to **automatically** handle placeholders like `<ACCOUNT_ID>`, `<REGION>`, and `<IMAGE_TAG>`.

- **`.github/workflows/terraform.yml`**: Automatically resolves the current AWS Account ID and Region, injecting them into the K8s manifests during the infra deployment.
- **`.github/workflows/deploy-frontend.yml`**: Automatically builds and pushes the frontend image, then updates the K8s deployment to use the specific Git commit SHA.
- **`.github/workflows/deploy-services.yml`**: Builds service images in GHCR, transfers successful builds into ECR, and applies only the matching backend manifests.

---

## Deployment Steps

### Step 1 — Initialize Terraform

```bash
cd infra/terraform
terraform init
```

### Step 2 — Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars → set db_password
```

### Step 3 — Preview Changes (dry run)

```bash
terraform plan -var-file=terraform.tfvars
```

Review the output — no resources are created yet.

### Step 4 — Apply Infrastructure

```bash
terraform apply -var-file=terraform.tfvars
# Type "yes" to confirm
```

> ⚠️ **This creates real AWS resources and incurs costs** (~$100+/month for EKS + NAT + RDS).

### Step 5 — Configure kubectl

```bash
aws eks update-kubeconfig --name hiring-system-dev --region ap-southeast-1
kubectl get nodes   # Should show the managed node group
```

### Step 6 — Deploy Kubernetes Resources

```bash
# Namespaces
kubectl apply -f k8s/namespaces.yaml

# Secrets (after editing secrets.yaml with real values)
cp k8s/secrets.yaml.example k8s/secrets.yaml
# Edit secrets.yaml with base64-encoded credentials
kubectl apply -f k8s/secrets.yaml

# Deployments + Services + HPAs
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/coordinator-agent-deployment.yaml
kubectl apply -f k8s/resume-intake-agent-deployment.yaml
kubectl apply -f k8s/screening-agent-deployment.yaml
kubectl apply -f k8s/skill-assessment-agent-deployment.yaml
kubectl apply -f k8s/audit-agent-deployment.yaml
kubectl apply -f k8s/ranking-agent-deployment.yaml
```

### Step 7 — Verify

```bash
kubectl get pods -n frontend        # Frontend on managed node group
kubectl get pods -n services        # Agents on Fargate
kubectl get svc -n frontend         # LoadBalancer → external URL
kubectl get hpa -n services         # HPA autoscalers
```

### Step 8 — Initialize Database Schema

**Option A (Automated — Recommended)**
Push any changes to `db/` or manually trigger the **"Deploy Database Changes"** GitHub Action. It automatically:
1. Installs the PostgreSQL client.
2. Resolves the live RDS endpoint via Terraform outputs.
3. Runs `db/init_db.sql`.
4. Applies all migrations in `db/migrations/*.sql`.

**Option B (Manual)**
```bash
# Get RDS endpoint from terraform output
terraform output rds_hostname

# Connect and run init_db.sql (from a pod or bastion)
kubectl run db-init --rm -it --image=postgres:15 -n services -- \
  psql -h <RDS_HOSTNAME> -U dbadmin -d hiring_system -f /dev/stdin < ../../db/init_db.sql
```

---

## Tear Down

```bash
# Delete LoadBalancer-type services to avoid orphaned AWS ALBs/Classic LBs ($0.54/day)
kubectl delete svc --all -n frontend --ignore-not-found=true
sleep 30

# Remove all other K8s resources
kubectl delete -f k8s/

# Destroy all AWS resources
terraform destroy -var-file=terraform.tfvars
```

---

## CI/CD Pipeline (GitHub Actions)

Deploy via GitHub Actions using `.github/workflows/terraform.yml`.

### Main Infrastructure Pipeline (`terraform.yml`)

```mermaid
graph LR
    D["Manual Dispatch"] --> V["Validate<br/>fmt + validate"]
    V --> P["Plan"]
    P --> A["Apply"]
    A --> K["Deploy K8s"]
```

The workflow runs Validate → Plan → Apply → Deploy K8s when triggered, and GitHub Environment protection rules may require approval before `apply` or `deploy-k8s`.

### Cost Optimization Pipeline (`terraform-manage.yml`)

A specialized, integrated workflow designed to reduce dev environment costs by destroying expensive resources over weekends/nights:

1. **Destroy Job**: Captures the image tags currently wired into the workflow, deletes the `frontend` LoadBalancer service (prevents orphaned AWS LBs), and destroys EKS Control Plane, Node Groups, Fargate, and NAT Gateway (~$4.14/day savings). Retains RDS, ECR, VPC, and IAM.
2. **Recreate Job**: Paused securely behind a GitHub Environment approval gate. Upon manual approval, creates the infrastructure back.
3. **Deploy K8s**: Restores the manifests currently handled by `terraform-manage.yml` using those captured image tags.

### Setup

1. Go to **GitHub → Settings → Secrets and variables → Actions**
2. Add these repository secrets:

| Secret | Value |
|--------|-------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key |
| `TF_VAR_DB_PASSWORD` | Database password |
| `OPENAI_API_KEY` | OpenAI API key (for K8s secrets) |

### Usage

1. Go to **Actions → Terraform Infrastructure → Run workflow**
2. Click **Run workflow**
3. The workflow proceeds through Validate → Plan → Apply → Deploy K8s, subject to any approvals configured on the target GitHub Environments.

## Current Workflow Note

- `deploy-services.yml` now dynamically builds and deploys successful services: `coordinator-agent`, `resume-intake-agent`, `screening-agent`, `skill-assessment-agent`, `ranking-agent`, and `audit-agent`.
- When adding new services, ensure both `terraform.yml` and `terraform-manage.yml` are also updated to capture and re-apply image tags.

---

## Key Notes

- **Kubernetes 1.32** was chosen because 1.29 extended support expires March 23, 2026. Version 1.32 has extended support until March 2027.
- **Single NAT Gateway** is used for cost optimization in dev. For production, use one NAT per AZ.
- **Fargate** is used for all service agents to enable serverless scaling. HPA auto-scales from 1→5 pods per service.
- **RDS** is single-AZ for dev. Enable `multi_az = true` in `variables.tf` for production.
