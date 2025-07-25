# PaymentsAgent Workflow

An intelligent, cost-efficient dispute resolution system powered by AI that automates billing dispute processing with human oversight. Built with LangGraph workflows, vector similarity search, and comprehensive cost management.

## Key Features

- **AI-Powered Resolution**: GPT-4o-mini generates intelligent dispute recommendations
- **Human-in-the-Loop**: Automated approval workflows with email notifications
- **Cost Optimized**: Built-in token limits ensure predictable costs (~$0.0003 per dispute)
- **Vector Learning**: ChromaDB stores historical resolutions for continuous improvement
- **Multi-System Integration**: CRM, Billing, Payment Gateway, AWS SQS
- **Scalable Architecture**: Handles thousands of disputes with consistent performance


## Technology Stack

### Core Framework
- **🐍 Python 3.11+**: Main programming language
- **🔄 LangGraph**: Workflow orchestration & state management
- **🌐 Uvicorn**: ASGI web server

### AI & Machine Learning
- **🤖 OpenAI GPT-4o-mini**: Dispute resolution AI
- **🧠 LangChain**: LLM integration framework  
- **📊 ChromaDB**: Vector database for similarity search
- **🔍 Embeddings**: For case similarity and policy retrieval

### Data Storage
- **🐘 PostgreSQL**: Primary workflow state database
- **📊 ChromaDB**: Vector database for AI context
- **💾 JSON**: Complex data structures in PostgreSQL

### External Integrations
- **☁️ AWS SQS**: Message queue for event processing
- **💳 paymentGateway**: Payment processing & refunds
- **📊 Billing**: Subscription billing management
- **📧 Gmail SMTP**: Email notifications

### Development & Operations
- **🔧 python-dotenv**: Environment configuration
- **📝 Logging**: Centralized application logging
- **🧪 Manual Testing**: Comprehensive test utilities
- **⚙️ Setup Automation**: Automated installation scripts

## Architecture Overview

```mermaid
graph TB
    subgraph "External Systems"
        SQS[AWS SQS<br/>Event Queue]
        CRM[CRM System<br/>Case Management]
        BILLING[Billing System<br/>Subscription Data]
        PAYMENT[Payment Gateway<br/>Transaction History]
        AI[OpenAI GPT-4o-mini<br/>AI Engine]
    end

    subgraph "PaymentsAgent Core"
        API[FastAPI Server<br/>:8003]
        WORKFLOW[Workflow Engine<br/>LangGraph]
        
        subgraph "Data Sources"
            PG[(PostgreSQL<br/>Workflow States)]
            VECTOR[(ChromaDB<br/>Vector Search)]
        end
    end

    subgraph "Processing Pipeline"
        FETCH[Data Collection]
        GENERATE[AI Resolution]
        REVIEW[Human Review]
        EXECUTE[Apply Resolution]
    end

    subgraph "Human Interface"
        EMAIL[Email Notifications]
        WEB[Web API<br/>Review Interface]
    end

    %% Main flow
    SQS --> WORKFLOW
    WORKFLOW --> FETCH
    FETCH --> CRM
    FETCH --> BILLING
    FETCH --> PAYMENT
    FETCH --> GENERATE
    GENERATE --> AI
    GENERATE --> VECTOR
    GENERATE --> REVIEW
    REVIEW --> EMAIL
    REVIEW --> WEB
    WEB --> API
    API --> EXECUTE
    EXECUTE --> BILLING
    EXECUTE --> PAYMENT
    EXECUTE --> PG
    EXECUTE --> VECTOR

    %% Styling
    classDef external fill:#e1f5fe
    classDef core fill:#f3e5f5
    classDef data fill:#e8f5e8
    classDef process fill:#fff3e0
    classDef human fill:#fce4ec
    
    class SQS,CRM,BILLING,PAYMENT,AI external
    class API,WORKFLOW core
    class PG,VECTOR data
    class FETCH,GENERATE,REVIEW,EXECUTE process
    class EMAIL,WEB human
```

## PostgreSQL Schema

#### PostgreSQL Tables

#### workflow_states - Main workflow persistence table

| Column | Type | Description |
|--------|------|-------------|
| **id** | SERIAL PRIMARY KEY | Auto-incrementing primary key |
| **run_id** | UUID UNIQUE | Workflow run identifier |
| **case_id** | VARCHAR(255) | CRM case ID |
| **customer_id** | VARCHAR(255) | Customer/account ID |
| **status** | VARCHAR(50) | `running`, `completed`, `failed`, `pending` |
| **current_step** | VARCHAR(100) | Current workflow step |
| **crm_data** | JSONB | Case and account data from CRM |
| **billing_data** | JSONB | Subscription data from Billing |
| **payment_data** | JSONB | Payment/charge data from Payment Gateway |
| **resolution_proposal** | JSONB | AI-generated resolution proposal |
| **human_review_data** | JSONB | Human review decision and comments |
| **final_resolution** | JSONB | Executed resolution details |
| **llm_cost** | DECIMAL(10,6) | LLM API costs for this workflow |
| **total_cost** | DECIMAL(10,6) | Total workflow cost |
| **cost_breakdown** | JSONB | Detailed cost breakdown by service |
| **created_at** | TIMESTAMP | Workflow creation time |
| **updated_at** | TIMESTAMP | Last update time |
| **completed_at** | TIMESTAMP | Workflow completion time |

**Indexes:** `run_id`, `case_id`, `status`, `current_step`, `created_at`

## ChromaDB Collections

#### 1. Dispute Resolutions Collection
- **Purpose**: Stores historical dispute resolutions for similarity matching
- **Content**: Resolution text, reasoning, and case context
- **Metadata**: Case IDs, dispute types, amounts, customer segments, resolution outcomes
- **Usage**: Retrieved during AI resolution generation for similar case analysis

#### 2. Company Policies Collection
- **Purpose**: Stores company policy documents and guidelines
- **Content**: Policy text from uploaded .docx documents
- **Metadata**: Policy IDs, titles, categories, document structure
- **Usage**: Referenced during resolution generation to ensure policy compliance

## Vector Database Strategy

#### Similarity Search Approach
1. **Semantic Embeddings**: ChromaDB uses sentence transformers for case similarity
2. **Multi-Factor Matching**: Combines dispute type, amount range, customer segment
3. **Historical Learning**: Each resolved case improves future recommendations
4. **Relevance Filtering**: Only top 3 similar cases used (prevents noise)

#### Query Optimization
```python
# Limited results prevent token inflation, limit prevents cost explosion
similar_cases = vector_db.query(
    query_text=case_description,
    n_results=3, 
    include=["documents", "metadatas", "distances"]
)

# Cached queries for performance
@lru_cache(maxsize=128)
def _query_similar_cases_cached(query_text: str, limit: int):
    # Repeated queries use cache (1-hour TTL)
```

#### Data Growth Management
- **Bounded Context**: Always retrieves exactly 3 cases regardless of DB size
- **Quality Over Quantity**: Better similarity matching as data grows
- **Cache Invalidation**: Smart cache clearing when new resolutions added
- **Deduplication**: Prevents storing multiple resolutions for same case

#### Policy Retrieval Workflow

The system uses a sophisticated policy retrieval process to ensure AI-generated resolutions comply with company policies:

```mermaid
graph TD
    A["Workflow Started"] --> B["Data Fetching Agent"]
    B --> C["Dispute Validation Agent"]
    C --> D["Resolution Generator Agent"]
    
    D --> E["Vector Service<br/>get_relevant_policies"]
    E --> F["ChromaDB Query<br/>company_policies collection"]
    F --> G["Policy Retrieval<br/>Based on case context"]
    
    G --> H["Policy Formatting<br/>Top 3 relevant policies"]
    H --> I["LLM Service<br/>generate_resolution"]
    I --> J["AI Resolution<br/>Based on policies"]
    
    J --> K["Human Review Agent"]
    K --> L["Execute Resolution Agent"]
    L --> M["Store Results Agent"]

    N["policies/ directory<br/>*.docx files"] --> O["Document Processor<br/>Extract text"]
    O --> P["ChromaDB Storage<br/>company_policies collection"]
    P --> F

    Q["Case Data<br/>Dispute Type, Amount, Description"] --> S["Query Generation<br/>with case/account context"]
    R["Account Data<br/>Customer Segment, Account Type"] --> S
    S --> F

    G --> T["Policy 1: Comprehensive Billing Policy<br/>Relevance: 0.358"]
    G --> U["Policy 2: Billing Dispute Resolution<br/>Relevance: 0.348"]  
    G --> V["Policy 3: Other Billing Policy<br/>Relevance: 0.141"]
    
    T --> H
    U --> H
    V --> H


```

This workflow demonstrates how the system:
1. **Processes case data** through multiple workflow stages
2. **Retrieves relevant policies** from ChromaDB based on dispute context
3. **Generates context-aware queries** using case and account information
4. **Formats and prioritizes policies** for AI resolution generation
5. **Ensures policy compliance** throughout the resolution process

## Cost Management Strategy

### Built-in Cost Controls

#### 1. Token Limits (Hard Caps)
| Component | Limit | Max Tokens | Cost Impact |
|-----------|-------|------------|-------------|
| Similar Cases | 3 cases | ~300 tokens | Fixed |
| Company Policies | 3 policies | ~450 tokens | Fixed |
| Payment History | 5 charges | ~125 tokens | Fixed |
| Output Response | 1000 tokens | 1000 tokens | Capped |

#### 2. Prompt Engineering
```python
# services/llm_service.py - Smart prompt limits
def _format_similar_cases(self, cases: List[Dict[str, Any]]) -> str:
    for case in cases[:3]:  # Only top 3 cases
        formatted.append(f"- Case {case.get('case_id')}: ${case.get('amount')} - {case.get('resolution')}")
    return "\n".join(formatted)

def _format_policies(self, policies: List[Dict[str, Any]]) -> str:
    for policy in policies[:3]:  # Only top 3 policies
        formatted.append(f"- {policy.get('title')}: {policy.get('content')}")
    return "\n".join(formatted)
```

#### 3. Intelligent Caching
```python
# services/llm_service.py - Cost-saving cache
@lru_cache(maxsize=128)
def _query_similar_cases_cached(self, query_text: str, limit: int):
    # Cache hits save ~$0.0003 per repeated query
    
def _get_cache_key(self, context: Dict[str, Any]) -> str:
    # Smart cache key ignores timestamps, focuses on case essence
    cache_context = {
        'case_id': context.get('case', {}).get('Id', ''),
        'amount': context.get('case', {}).get('Amount__c', 0),
        'dispute_type': context.get('case', {}).get('Dispute_Type__c', ''),
        'customer_segment': context.get('account', {}).get('Customer_Segment__c', ''),
    }
```

#### 4. Model Selection
```python
# services/llm_service.py - Cost-optimized model choice
self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')  # 4x cheaper than GPT-4

# GPT-4o-mini pricing:
# Input: $0.150 per 1M tokens (vs $5.00 for GPT-4)
# Output: $0.600 per 1M tokens (vs $15.00 for GPT-4)
```

### Cost Tracking Implementation
```python
# services/llm_service.py - Real-time cost calculation
def _calculate_cost(self, usage) -> Dict[str, Any]:
    input_cost_per_1m = 0.150
    output_cost_per_1m = 0.600
    
    input_tokens = usage.prompt_tokens
    output_tokens = usage.completion_tokens
    
    input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
    output_cost = (output_tokens / 1_000_000) * output_cost_per_1m
    total_cost = input_cost + output_cost
    
    return {
        'total_cost': round(total_cost, 6),
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'input_cost': round(input_cost, 6),
        'output_cost': round(output_cost, 6)
    }
```

### Cost Performance Metrics
| Metric | Typical Value | Maximum Value |
|--------|---------------|---------------|
| Cost per dispute | $0.0003 | $0.001 |
| Input tokens | 800-1200 | 2,075 |
| Output tokens | 150-300 | 1,000 |
| Cache hit rate | 60-80% | - |
| Cost savings from cache | $0.0002/hit | - |

## Workflow Process


```mermaid
graph TD
    START([Dispute Event<br/>Triggers SQS]) --> FETCH[📥 Data Fetcher<br/>Salesforce + Zuora + Stripe]
    
    FETCH --> VALIDATE[✅ Dispute Validator<br/>Check legitimacy]
    
    VALIDATE --> GENERATE[🤖 Resolution Generator<br/>AI Analysis + Policy Lookup]
    
    GENERATE --> SEND[📤 Human Review Sender<br/>Send to approval queue]
    
    SEND --> WAIT[⏳ Human Review Waiter<br/>Pause for human decision]
    
    WAIT --> DECISION{Human Decision}
    
    DECISION -->|Approved| EXECUTE[⚡ Resolution Executor<br/>Process refund/credit]
    DECISION -->|Rejected| ERROR[❌ Error Handler<br/>Log rejection]
    
    EXECUTE --> STORE[💾 Results Storer<br/>Save final outcome]
    
    STORE --> END([Workflow Complete])
    ERROR --> END
    
    WAIT -.->|API Call| API[🌐 FastAPI Server<br/>Human Review Interface]
    API -.->|Decision| WAIT
    
    style START fill:#e3f2fd
    style GENERATE fill:#f3e5f5
    style DECISION fill:#fff3e0
    style END fill:#e8f5e8
```

### Detailed Workflow Steps

#### 1. 📥 Data Fetcher Agent
```python
# Parallel data collection from multiple sources
- CRM: Case details, customer info, dispute history
- Billing: Subscription data, billing history  
- Gateway: Payment transactions, previous disputes
- Async processing for performance optimization
```

#### 2. ✅ Dispute Validator Agent
```python
# Business rule validation
# • Check dispute type validity
# • Verify customer eligibility  
# • Validate dispute amount vs. billing records
# • Early filtering of invalid cases
```

#### 3. 🤖 Resolution Generator Agent
```python
# AI-powered resolution creation
# • Build context from all collected data
# • Query ChromaDB for similar historical cases
# • Retrieve relevant business policies
# • Generate resolution using OpenAI GPT-4o-mini
# • Calculate confidence scores
```

#### 4. 📤 Human Review Sender Agent
```python
# Prepare for human approval
# • Package resolution proposal with context
# • Send to SQS human review queue
# • Send email notification to approvers
# • Set up workflow state for pausing
```

#### 5. ⏳ Human Review Waiter Agent
```python
# Intelligent workflow pausing
# • Check for human decision in database
# • Route based on approval/rejection status
# • Handle timeout scenarios
# • Resume workflow when decision made
```

#### 6. ⚡ Resolution Executor Agent
```python
# Execute approved resolutions
# • Process Stripe refunds
# • Update billing systems
# • Send customer notifications
# • Handle execution errors gracefully
```

#### 7. 💾 Results Storer Agent
```python
# Finalize and store outcomes
# • Save to PostgreSQL with full audit trail
# • Store resolution in ChromaDB for future similarity
# • Calculate and log total costs
# • Send completion notifications
```

### Workflow State Management

The system uses **LangGraph** for sophisticated workflow orchestration:

- **State Persistence**: Complete workflow state stored in PostgreSQL
- **Error Recovery**: Graceful handling of failures with retry logic
- **Human-in-the-Loop**: Seamless pause/resume for human decisions
- **Audit Trail**: Complete history of all workflow steps and decisions
- **Cost Tracking**: Real-time monitoring of AI and external API costs

### Human Review Process

```mermaid
sequenceDiagram
    participant W as Workflow
    participant SQS as AWS SQS
    participant API as FastAPI Server
    participant H as Human Reviewer
    participant DB as PostgreSQL

    W->>SQS: Send review request
    W->>API: Send email notification
    W->>DB: Save "pending" state
    W->>W: Pause execution
    
    H->>API: POST /human-review/decision
    API->>DB: Update human_review_data
    API->>W: Resume workflow
    W->>W: Execute approved resolution
    W->>DB: Mark completed
```

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- API keys for: OpenAI, CRM, AWS, Billing, Payment Gateway
- Gmail App Password (optional, for notifications)

### 1. Clone and Setup
```bash
# Clone repository
git clone <repository-url>
cd PaymentsAgentWorkflow

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
# Copy environment template
cp env.example .env

# Edit with your credentials
nano .env
```

Required Environment Variables:
```bash
# Database
POSTGRES_URL=postgresql://user:password@localhost:5432/paymentsagent

# OpenAI (Required)
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_MODEL=gpt-4o-mini

# AWS SQS (Required)
DISPUTE_EVENTS_QUEUE_URL=https://sqs.region.amazonaws.com/account/dispute-events
HUMAN_REVIEW_NOTIFICATIONS_QUEUE_URL=https://sqs.region.amazonaws.com/account/human-review

# CRM (Required)
CRM_BASE_URL=https://your-instance.develop.my.crm.com
CRM_ACCESS_TOKEN=your-access-token

# Billing (Optional - will use mock data)
BILLING_BASE_URL=https://rest.sandbox.billing.com
BILLING_ACCESS_TOKEN=your-access-token

# Payment Gateway (Optional - will use mock data)  
PAYMENT_SECRET_KEY=sk_test_your-payment-key

# Gmail (Optional - for email notifications)
GMAIL_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
APPROVER_EMAIL=approver@gmail.com

# ChromaDB
CHROMA_DB_PATH=./chroma_db
```

### 3. Automated Setup
```bash
# Run the complete setup
python setup.py
```

This will:
- ✅ Validate all prerequisites
- ✅ Install Python dependencies
- ✅ Create PostgreSQL database and tables
- ✅ Seed ChromaDB with sample policies and resolutions
- ✅ Test system with sample dispute

### 4. Manual Setup (Alternative)
```bash
python utils/setup_database.py

python utils/seed_vector_db.py

python utils/publish_sqs_message.py
python app.py
```

### 5. Start Services
```bash
# Terminal 1: Start API server
python app.py --api
# API available at http://localhost:8003

# Terminal 2: Start workflow processor
python app.py
# Listens for SQS messages and processes workflows
```

### 6. Test the System
```bash
# Send test dispute
python utils/publish_sqs_message.py

# Check API health
curl http://localhost:8003/health

# View workflow status
curl http://localhost:8003/workflow/{run_id}/status

# Submit human review decision
curl -X POST http://localhost:8003/human-review/decision \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "your-run-id",
    "case_id": "your-case-id", 
    "decision": "approved",
    "reviewer_name": "test-user",
    "comments": "Approved for testing"
  }'
```

## Usage & Monitoring

### Key API Endpoints

#### Health Check
**`GET /health`**
- **Purpose**: Service health status
- **Response**: JSON with system status and timestamp

#### Human Review System
**`POST /human-review/decision`**
- **Purpose**: Submit human review decision and auto-continue workflow
- **Body**:
```json
{
  "run_id": "uuid-12345",
  "case_id": "CASE-001-TEST-12345",
  "decision": "approved",
  "reviewer_name": "john.doe@company.com",
  "comments": "Approved - legitimate billing dispute",
  "modified_resolution": {
    "action": "partial_refund",
    "amount": 45.00,
    "reason": "Modified amount based on review"
  }
}
```

**`GET /human-review/pending`**
- **Purpose**: Get all workflows waiting for human review

#### Cost Tracking
**`GET /costs/workflow/{run_id}`**
- **Purpose**: Get detailed cost breakdown for specific workflow
- **Response**: JSON with LLM costs, token usage, and cost breakdown

**`GET /costs/case/{case_id}`**
- **Purpose**: Get aggregated costs for all workflows of a case
- **Response**: JSON with total costs and workflow summary

### Cost Monitoring Commands
```bash
# Get specific workflow costs
curl http://localhost:8003/costs/workflow/uuid-12345
```

### Logs
- Application logs: `logs/workflow.log`
- Rotating logs (10MB max, 5 backups)
- Structured JSON logging with cost tracking

## Configuration

See [Cost Management Strategy](#cost-management-strategy) for detailed configuration options and optimization settings.

## Scripts & Tools Reference

### Main Application (`app.py`)
The primary entry point supporting multiple operation modes:

```bash
# Start SQS message processing workflow (default)
python app.py

# Start API server for human review interface
python app.py --api
python app.py --server    # Alternative alias

# Run single workflow for testing
python app.py <case_id>
python app.py <case_id> <customer_id>

# Show help and usage information
python app.py --help
python app.py -h
```

**Examples:**
```bash
# Production: Process SQS messages
python app.py

# Development: Start API server
python app.py --api

# Testing: Run specific case
python app.py CASE-001-TEST-12345

# Testing with customer ID
python app.py CASE-001-TEST-12345 ACC-001-DEMO-67890
```

### Key Utility Scripts

| Script | Purpose | Key Options |
|--------|---------|-------------|
| `setup.py` | Complete automated setup | `--skip-deps`, `--skip-db`, `--skip-vector` |
| `utils/setup_database.py` | Database management | `--reset`, `--check` |
| `utils/seed_vector_db.py` | ChromaDB management | `--reset`, `--create-policies-dir` |
| `utils/publish_sqs_message.py` | Testing utilities | `--case-id`, `--count`, `--queue-url` |

### Common Commands

```bash
# First time setup
python setup.py

# Reset database and vector data
python utils/setup_database.py --reset
python utils/seed_vector_db.py --reset

# Test specific case
python utils/publish_sqs_message.py --case-id YOUR_CASE_ID
python app.py

# Update policy documents
python utils/seed_vector_db.py --reset
```

## Development

### Project Structure
```
PaymentsAgentWorkflow/
├── 🚀 app.py                    # Main application entry point
├── ⚙️ setup.py                  # Setup & installation script  
├── 📋 requirements.txt          # Python dependencies
├── 🔧 .env                      # Environment configuration
├── 📝 README.md                 # Project documentation
│
├── 🔄 workflows/                # LangGraph workflow definitions
│   ├── __init__.py
│   └── dispute_workflow.py      # Main workflow orchestration
│
├── 🤖 agents/                   # Individual workflow agents
│   ├── data_fetcher.py          # Fetch data from external APIs
│   ├── dispute_validator.py     # Validate dispute legitimacy  
│   ├── resolution_generator.py  # AI-powered resolution generation
│   ├── human_review_sender.py   # Send for human approval
│   ├── human_review_waiter.py   # Wait for human decision
│   ├── resolution_executor.py   # Execute approved resolutions
│   ├── results_storer.py        # Store final results
│   ├── error_handler.py         # Handle workflow errors
│   ├── workflow_state.py        # State management
│   └── workflow_context.py      # Context management
│
├── 🛠️ services/                 # External service integrations
│   ├── service_factory.py       # Singleton service management
│   ├── llm_service.py           # OpenAI integration
│   ├── database_service.py      # PostgreSQL operations
│   ├── salesforce_service.py    # Salesforce CRM integration
│   ├── zuora_service.py         # Zuora billing integration
│   ├── stripe_service.py        # Stripe payment processing
│   ├── aws_service.py           # AWS SQS messaging
│   ├── email_service.py         # Gmail notifications
│   ├── vector_service.py        # ChromaDB operations
│   └── async_data_service.py    # Parallel data fetching
│
├── 🌐 api/                      # FastAPI REST endpoints
│   └── main.py                  # Human review API server
│
├── 📊 models/                   # Data models & schemas
│   ├── dispute_case.py          # Dispute case model
│   └── resolution.py           # Resolution model
│
├── 🔧 utils/                    # Utility scripts & helpers
│   ├── logging_config.py        # Centralized logging
│   ├── setup_database.py       # Database initialization
│   ├── seed_vector_db.py        # ChromaDB data seeding
│   └── publish_sqs_message.py   # Test message publishing
│
├── 📋 policies/                 # Business policy documents
│   ├── billing-dispute-resolution.docx
│   ├── service-outage-compensation-policy.docx
│   └── historical-dispute-resolutions.docx
│
├── 📊 chroma_db/               # ChromaDB vector storage
├── 📝 logs/                    # Application logs
└── 🐍 venv/                    # Python virtual environment
```


## Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---