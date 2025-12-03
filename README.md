# AWS Copilot Deployment Template

This is a template repository that deploys a sample React Next.js application to AWS using [AWS Copilot](https://aws.github.io/copilot-cli/). The repository includes a GitHub Actions workflow for automated deployment to your AWS sandbox account.

## What is AWS Copilot?

AWS Copilot is an open-source command-line interface that simplifies building, releasing, and operating production-ready containerized applications on AWS. Instead of manually configuring AWS services, Copilot automates the setup and deployment process.

### What Copilot Builds for You Behind the Scenes

When you use AWS Copilot, it automatically provisions and configures:

- **Amazon ECS (Elastic Container Service)**: Manages your containerized application
- **AWS Fargate**: Serverless compute engine that runs your containers without managing servers
- **Application Load Balancer (ALB)**: Distributes incoming traffic across your containers
- **Amazon ECR (Elastic Container Registry)**: Stores your Docker images securely
- **VPC, Subnets, and Security Groups**: Network infrastructure to isolate and secure your application
- **IAM Roles and Policies**: Proper permissions for your services to interact with AWS resources
- **CloudFormation Stacks**: Infrastructure as Code for repeatable deployments
- **CloudWatch Logs**: Centralized logging for monitoring your application

All of this infrastructure is created automatically based on best practices, allowing you to focus on your application code rather than AWS configuration.

## Understanding Copilot Concepts

AWS Copilot organizes your infrastructure using three key concepts:

### Applications

An **Application** is the highest-level logical grouping for your entire project or product. It's a collection of related services and environments. 

**Example:** You might have an application named `"chat"` that represents your entire chat platform.

### Environments

An **Environment** represents a deployment stage (e.g., development, staging, production). Each environment is completely isolated and contains its own set of AWS resources (VPC, ECS cluster, load balancer, etc.).

**Example:** Within your `"chat"` application, you might have:
- `dev` - Development environment for testing
- `prod` - Production environment serving real users

### Services

A **Service** is a specific component or microservice of your application. Each service runs in containers and can be deployed to multiple environments. Services share the environment's infrastructure (network, cluster, load balancer).

**Example:** Your `"chat"` application might have multiple services:
- `frontend` - React/Next.js web interface
- `api` - Backend REST API
- `websocket` - Real-time messaging service

### Putting It Together

**A single application and environment can support multiple services.** For example:

```
Application: "ecommerce"
├── Environment: "dev"
│   ├── Service: "frontend" (Next.js web app)
│   ├── Service: "api" (Backend API)
│   └── Service: "worker" (Background job processor)
└── Environment: "prod"
    ├── Service: "frontend"
    ├── Service: "api"
    └── Service: "worker"
```

In this example, you have:
- 1 Application (`ecommerce`)
- 2 Environments (`dev` and `prod`)
- 3 Services (`frontend`, `api`, `worker`)

Each service can be deployed independently to each environment, giving you full control over your deployment strategy.

## GitHub Actions Deployment

This repository includes a GitHub Actions workflow (`.github/workflows/deploy.yaml`) that automates deployment to AWS. The workflow:

1. Discovers your Copilot application, environments, and services
2. Deploys all environments in parallel
3. Deploys all services to their respective environments

### Required Repository Secrets

The GitHub Action uses repository secrets to authenticate with your AWS account. You'll need to configure these in your repository settings:

**Repository Variables:**
- `AWS_ACCESS_KEY_ID` - Your AWS access key ID
- `AWS_REGION` - AWS region (typically `us-east-1`)

**Repository Secrets:**
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret access key

These credentials are obtained from your AWS Workshop Studio sandbox environment (see Prerequisites section below).

## Prerequisites

Before you begin, ensure you have the following:

### 1. Install AWS Copilot CLI

#### macOS

Using Homebrew:
```bash
brew install aws/tap/copilot-cli
```

Or manually:
```bash
curl -Lo copilot https://github.com/aws/copilot-cli/releases/latest/download/copilot-darwin && \
chmod +x copilot && \
sudo mv copilot /usr/local/bin/copilot && \
copilot --help
```

#### Windows

Open PowerShell as Administrator and run:
```powershell
Invoke-WebRequest -OutFile 'C:\Program Files\copilot.exe' https://github.com/aws/copilot-cli/releases/latest/download/copilot-windows.exe
```

**Note:** Use Windows Terminal for the best experience.

### 2. Configure AWS Credentials

You need to set up AWS credentials from your AWS Workshop Studio sandbox account.

1. Navigate to your AWS Workshop Studio event dashboard
2. Click **"Get AWS CLI credentials"**
3. Copy the credentials shown in the modal

The credentials will look like this:

![AWS CLI Credentials Modal](docs/images/aws-credentials-modal.png)
*Example: AWS Workshop Studio credentials dialog*

You can configure these credentials in one of two ways:

#### Option A: AWS Profile (Recommended for local development)

Create or update `~/.aws/credentials`:

```bash
[your-profile-name]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
aws_session_token = YOUR_SESSION_TOKEN
region = us-east-1
```

#### Option B: Environment Variables (For CI/CD or temporary use)

When running via Github Actions, these environment variables are automatically injected.

```bash
export AWS_DEFAULT_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY"
```

**Important:** Workshop Studio credentials are temporary and expire after a few hours. You'll need to refresh them periodically.

## Getting Started

Follow these steps to set up and deploy your application using AWS Copilot.

### Step 1: Application Creation

Initialize a new Copilot application. The application name is a logical grouping for your entire project (not an individual component).

```bash
copilot app init myapp
```

**Example:**
- ✅ Good: `copilot app init ecommerce-platform`
- ❌ Avoid: `copilot app init frontend` (too specific, use this for service names)

### Step 2: Environment Creation

Create an environment where your services will be deployed. For workshop purposes, we'll create a `dev` environment in `us-east-1`.

```bash
copilot env init --name dev --region us-east-1 --default-config
```

When prompted, you'll see:

```
Which credentials would you like to use to create your environment?
  > [profile your-profile-name]
    Enter temporary credentials
```

- If you created an AWS profile (Option A above), select your profile
- If using temporary credentials (Option B above), select **"Enter temporary credentials"** and paste the values from the AWS Workshop Studio

Copilot will then create your environment infrastructure, which takes approximately 5-10 minutes.

### Step 3: Service Creation

Create a service within your application. A service represents a deployable component (e.g., a web frontend, API, worker).

```bash
copilot svc init
```

Copilot will prompt you with several questions:

#### 1. Select Workload Type

```
Which workload type best represents your service?
  > Load Balanced Web Service
    Backend Service
    Request-Driven Web Service
    Static Site
    Worker Service
```

**For most web applications, choose "Load Balanced Web Service"** - this creates a service behind an Application Load Balancer that can handle HTTP/HTTPS traffic.

#### 2. Name Your Service

```
What do you want to name this service?
```

Enter a descriptive name for your service component:
- Examples: `frontend`, `api`, `admin-dashboard`, `payment-service`

#### 3. Select Dockerfile

```
Which Dockerfile would you like to use for your service?
```

Point Copilot to your Dockerfile. For this template repository:

```
./Dockerfile
```

#### 4. Port Configuration

Copilot will scan your Dockerfile for `EXPOSE` directives. 

- If found, it will automatically use the exposed port
- If not found, you'll be prompted to enter a port manually (e.g., `3000` for Next.js)

**Note:** If you encounter port issues, ensure your Dockerfile includes:
```dockerfile
EXPOSE 3000
```

Copilot will then:
- Create a service manifest at `copilot/[service-name]/manifest.yml`
- Set up the infrastructure configuration

#### 5. Configure Network Binding (Important!)

After service creation, you need to update the service manifest to ensure your application listens on all network interfaces (required for containers). This sets the `HOST` and `HOSTNAME` environment variables to `0.0.0.0`.

**Prerequisites:** Install `yq` if you don't have it:
- macOS: `brew install yq`
- Linux: Download from [https://github.com/mikefarah/yq/releases](https://github.com/mikefarah/yq/releases)

Run the following command to update all service manifests:

```bash
find copilot -type f -name manifest.yml -not -path "*/environments/*" -print0 | \
while IFS= read -r -d '' file; do
  yq -i '
    .variables.HOST = "0.0.0.0" |
    .variables.HOSTNAME = "0.0.0.0"
  ' "$file"
  echo "Updated: $file"
done
```

This command:
- Finds all service manifest files (excluding environment manifests)
- Creates a backup of each manifest file (`.bak`)
- Adds `HOST: "0.0.0.0"` and `HOSTNAME: "0.0.0.0"` to the `variables` section
- Confirms each update

**Note:** This step is critical for Next.js and many other applications to properly accept incoming connections in the container environment.

### Step 4: Commit Copilot Configuration

After initialization, commit the generated Copilot configuration to your Git repository:

```bash
git add copilot/
git commit -m "Add Copilot configuration"
git push origin main
```

The `copilot/` directory structure will look like:
```
copilot/
├── .workspace
├── environments/
│   └── dev/
│       └── manifest.yml
└── [service-name]/
    └── manifest.yml
```

## Deployment

Once your Copilot configuration is set up, you have two options for deployment:

### Automated Deployment (Recommended)

The GitHub Actions workflow automatically deploys your application whenever you push to the `main` branch.

1. Ensure repository secrets are configured (see "Required Repository Secrets" above)
2. Push your changes to the `main` branch:
   ```bash
   git push origin main
   ```
3. Monitor the deployment in the **Actions** tab of your GitHub repository

The workflow will:
- Deploy all environments
- Build and push Docker images to ECR
- Deploy all services to their respective environments

### Manual Deployment

For quick testing or local deployments, you can manually deploy a service:

```bash
copilot svc deploy --name [service-name] --env [environment-name]
```

**Example:**
```bash
copilot svc deploy --name frontend --env dev
```

This will:
1. Build your Docker image locally
2. Push the image to Amazon ECR
3. Deploy the service to the specified environment
4. Display the service URL when deployment completes

## Useful Commands

Once your application is deployed, here are some helpful commands:

### View Application Status
```bash
copilot app show
```

### List Services
```bash
copilot svc ls
```

### View Service Details
```bash
copilot svc show --name [service-name]
```

### View Service Logs
```bash
copilot svc logs --name [service-name] --env [environment-name] --follow
```

### Access Service URL
```bash
copilot svc show --name [service-name] --env [environment-name]
```

Look for the "Routes" section in the output to find your service URL.

### Delete Resources

When you're done and want to clean up:

```bash
# Delete a service
copilot svc delete --name [service-name]

# Delete an environment
copilot env delete --name [environment-name]

# Delete the entire application
copilot app delete
```

## Project Structure

```
.
├── .github/
│   └── workflows/
│       └── deploy.yaml          # GitHub Actions deployment workflow
├── copilot/                      # Copilot configuration (generated)
│   ├── .workspace               # Application metadata
│   ├── environments/            # Environment configurations
│   └── [service-name]/          # Service configurations
├── sample-app/                   # Next.js application
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
├── Dockerfile                    # Docker build configuration
└── README.md                     # This file
```

## Additional Resources

For more information about AWS Copilot:

- [AWS Copilot Documentation](https://aws.github.io/copilot-cli/)
- [Copilot Concepts Overview](https://aws.github.io/copilot-cli/docs/concepts/overview/)
- [Copilot CLI Commands](https://aws.github.io/copilot-cli/docs/commands/init/)
- [Service Manifest Reference](https://aws.github.io/copilot-cli/docs/manifest/overview/)

## Troubleshooting

### "Credentials expired" error
Workshop Studio credentials are temporary. Return to your event dashboard and click "Get AWS CLI credentials" again to refresh them.

### "Port not found" during service init
Add an `EXPOSE` directive to your Dockerfile or manually specify the port when prompted.

### Service won't deploy
Check CloudWatch Logs for your service:
```bash
copilot svc logs --name [service-name] --env [environment-name]
```

### GitHub Actions failing
Verify that repository secrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.) are correctly configured in your repository settings.

## License

This template is provided as-is for educational and workshop purposes.

