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
├── ecr.tf                   # ECR repos (4) with scan-on-push & lifecycle
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
    └── secrets.yaml.example                 # Template for credentials

.github/workflows/
└── terraform.yml            # CI/CD pipeline (manual dispatch)
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
                end
            end
            RDS[("RDS PostgreSQL 15<br/>db.t3.micro<br/>Encrypted")]
        end
    end

    ECR["ECR<br/>(4 repositories)"]

    Internet --> IGW --> ALB --> FE
    COORD --> RDS
    RESUME --> RDS
    SCREEN --> RDS
    AUDIT --> RDS
    RANKING --> RDS
    PrivSub --> NAT --> IGW
    EKS -.-> ECR
```

| Component | Details |
|-----------|---------|
| **VPC** | `10.0.0.0/16`, 2 AZs (`ap-southeast-1a`, `1b`), single NAT (cost-optimized) |
| **EKS** | K8s 1.32, public+private endpoint, API/audit/authenticator logging. Root & all IAM users granted ClusterAdmin via Access Entries. |
| **Node Group** | `t3.small`, 1–4 nodes (managed node group), hosts the `frontend` namespace. |
| **Fargate** | `services` namespace — coordinator, resume-intake, screening, audit, ranking agents |
| **RDS** | PostgreSQL 15, gp2 storage (20 GB), 0-day backups (Free Tier) |
| **ECR** | 4 repos, immutable tags, scan-on-push, 10-image lifecycle cleanup |
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
```

### Step 7 — Verify

```bash
kubectl get pods -n frontend        # Frontend on managed node group
kubectl get pods -n services        # Agents on Fargate
kubectl get svc -n frontend         # LoadBalancer → external URL
kubectl get hpa -n services         # HPA autoscalers
```

### Step 8 — Initialize Database Schema

```bash
# Get RDS endpoint from terraform output
terraform output rds_endpoint

# Connect and run init_db.sql (from a pod or bastion)
kubectl run db-init --rm -it --image=postgres:15 -n services -- \
  psql "postgresql://dbadmin:YOUR_PASSWORD@hiring-system-dev-postgres.c9essouqsmqs.ap-southeast-1.rds.amazonaws.com:5432/hiring_system" \
  -f /dev/stdin < ../../db/init_db.sql
```

---

## Tear Down

```bash
# Remove K8s resources first
kubectl delete -f k8s/

# Destroy all AWS resources
terraform destroy -var-file=terraform.tfvars
```

---

## CI/CD Pipeline (GitHub Actions)

Deploy via GitHub Actions using `.github/workflows/terraform.yml`.

### Pipeline Structure

```mermaid
graph LR
    D["Manual Dispatch"] --> V["Validate<br/>fmt + validate"]
    V --> P["Plan"]
    P --> A["Apply"]
    A --> K["Deploy K8s"]
```

All jobs run **automatically end-to-end** when triggered — no environment approval gates needed.

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
3. All 4 jobs execute automatically: Validate → Plan → Apply → Deploy K8s

---

## Key Notes

- **Kubernetes 1.32** was chosen because 1.29 extended support expires March 23, 2026. Version 1.32 has extended support until March 2027.
- **Single NAT Gateway** is used for cost optimization in dev. For production, use one NAT per AZ.
- **Fargate** is used for all service agents to enable serverless scaling. HPA auto-scales from 1→5 pods per service.
- **RDS** is single-AZ for dev. Enable `multi_az = true` in `variables.tf` for production.
