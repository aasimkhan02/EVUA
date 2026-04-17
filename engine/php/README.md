# EVUA — PHP Migration Tool with Advanced Features

A comprehensive hybrid rule-based + AI-powered PHP version migration engine with Monaco editor integration, version control, risk assessment, and AI verification.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Git
- Gemini API key (optional, can use mock AI)

### Installation

```bash
# 1. Install Python dependencies
cd /e/Dev/major-proj/new_evua/evua/backend
pip install -r requirements.txt

# 2. Install frontend dependencies
cd ../frontend
npm install

# 3. Create environment files
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### Running the Project

#### Option A: Docker Compose (Recommended)

```bash
cd /e/Dev/major-proj/new_evua/evua
docker-compose up --build
```

The application will be available at:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

#### Option B: Manual Startup

```bash
# Terminal 1: Backend
cd /e/Dev/major-proj/new_evua/evua/backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd /e/Dev/major-proj/new_evua/evua/frontend
npm run dev
```

## 📋 Features

### 1. **Monaco Editor Integration** ✅
- Side-by-side code comparison with syntax highlighting
- Support for PHP, HTML, CSS, JavaScript
- Real-time diff display
- Code statistics (lines, bytes)

**How to use:**
- Upload PHP files for migration
- Navigate to Results page
- Click on a file to view the diff in Monaco editor
- Compare original vs migrated code side-by-side

### 2. **Git-Based Version Control** ✅
- Track all migration changes as git commits
- Branch-like revert (creates new commit instead of replacing)
- View complete version history
- Compare between any two versions

**API Endpoints:**
```bash
# Initialize version control
POST /api/versions/{job_id}/init

# Get version history
GET /api/versions/{job_id}/history

# Create a new version
POST /api/versions/{job_id}/create

# Get diff between versions
GET /api/versions/{job_id}/diff?from_commit=X&to_commit=Y

# Preview revert operation
GET /api/versions/{job_id}/revert-preview?target_commit=HASH

# Apply revert
POST /api/versions/{job_id}/revert?target_commit=HASH
```

### 3. **Risk Assessment & Benchmarking** ✅
Automatically evaluates each migrated file for risk based on:

- **Code Complexity** - Lines of code, nesting depth, function count
- **Dependencies** - External library calls, deprecated APIs
- **Pattern Complexity** - Dynamic variables, eval, magic methods
- **Issue Count** - Number of detected problems
- **Change Size** - Percentage of code that changed
- **AI Confidence** - Trust level in AI-generated code

**Risk Categories:**
- `LOW` (< 0.25) - Safe to deploy
- `MEDIUM` (0.25-0.6) - Review recommended
- `HIGH` (0.6-0.8) - AI verification recommended
- `CRITICAL` (≥ 0.8) - Mandatory AI verification

**API Endpoints:**
```bash
# Assess risk for a file
POST /api/risk/assess

# Get risk summary for job
GET /api/risk/{job_id}/summary

# Get files needing AI review
GET /api/risk/{job_id}/critical
```

### 4. **AI Verification Pipeline** ✅
Automatically processes high-risk code through Gemini AI:

- Identifies potential runtime errors, logic bugs, security issues
- Provides suggested corrections
- Tracks confidence level of suggestions
- Allows manual approval/rejection
- Auto-applies fixes with user consent

**AI checks for:**
- Runtime errors and PHP 8 compatibility
- Logic bugs and unexpected behavior
- Performance degradation
- Security vulnerabilities
- Type system violations

**API Endpoints:**
```bash
# Verify a single file
POST /api/ai/verify/{job_id}

# Batch verify multiple high-risk files
POST /api/ai/verify-batch/{job_id}

# Get all verifications for job
GET /api/ai/verify/{job_id}/results

# Approve a suggestion
POST /api/ai/verify/{section_id}/approve

# Reject a suggestion
POST /api/ai/verify/{section_id}/reject

# Apply suggested fix
POST /api/ai/verify/{section_id}/apply
```

### 5. **Database & Persistence** ✅
SQLite database stores:
- Migration job metadata
- Version snapshots and git commits
- Risk assessment scores and metrics
- AI verification feedback
- Change audit trail

Database file: `/evua/backend/storage/evua.db`

## 📊 Complete Workflow

```
1. Upload PHP Files
   └─> Files stored in /evua/backend/upload

2. Run Migration
   ├─> Migration engine processes files
   ├─> Rule engine applies auto-fixes
   ├─> Issues requiring AI are collected
   └─> Initial version committed to git

3. Risk Assessment (Automatic)
   ├─> Analyzes code complexity
   ├─> Evaluates dependencies & patterns
   ├─> Checks issue count
   ├─> Calculates overall risk score
   └─> Stores results in database

4. AI Verification (Automatic for HIGH/CRITICAL)
   ├─> Identifies high-risk files
   ├─> Sends to Gemini for analysis
   ├─> Receives suggestions with confidence
   ├─> Stores verifications in database
   └─> Creates new version if fixes applied

5. Version Control
   ├─> Each stage creates git commit
   ├─> Full history accessible
   ├─> Can revert to any version
   └─> Shows detailed diffs

6. Review & Deployment
   ├─> View Monaco editor showing changes
   ├─> Approve/reject AI suggestions
   ├─> Apply fixes incrementally
   ├─> Test changes (manual)
   └─> Deploy when confident
```

## 🏗️ Architecture

```
evua/
├── engine/                    ← Python AST parser + rule engine
│   ├── ast_parser/
│   ├── rule_engine/
│   ├── ai_processor/
│   ├── pipeline/
│   └── utils/
│
├── backend/                   ← FastAPI server
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── migration.py
│   │   │   ├── versions.py
│   │   │   ├── risk.py
│   │   │   ├── ai_verify.py
│   │   │   └── health.py
│   │   ├── services/
│   │   │   ├── migration_service.py
│   │   │   ├── version_control_service.py
│   │   │   ├── risk_assessment_service.py
│   │   │   └── ai_verification_service.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   ├── schemas/
│   │   │   ├── migration.py
│   │   │   ├── version.py
│   │   │   ├── risk.py
│   │   │   └── ai_verify.py
│   │   └── main.py
│   ├── storage/
│   │   ├── versions/          ← Git repos per job
│   │   ├── uploads/           ← Uploaded PHP files
│   │   └── evua.db            ← SQLite database
│   └── requirements.txt
│
├── frontend/                  ← React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── diff/          ← Monaco diff viewer
│   │   │   ├── version/       ← Version control UI
│   │   │   ├── risk/          ← Risk dashboard
│   │   │   └── ai/            ← AI verification UI
│   │   ├── pages/
│   │   │   ├── ResultsPage.jsx
│   │   │   ├── VersionControlPage.jsx
│   │   │   ├── RiskDashboardPage.jsx
│   │   │   └── AIReviewPage.jsx
│   │   └── services/          ← API clients
│   └── package.json
│
└── docker-compose.yml
```

## 🔧 Configuration

### Backend Environment Variables

```env
# .env file
GEMINI_API_KEY=your-api-key-here
DEBUG=true
CORS_ORIGINS=http://localhost:5173
MAX_UPLOAD_SIZE_MB=50
MAX_CONCURRENCY=5
```

### Frontend Environment Variables

```env
# .env file
VITE_API_BASE_URL=http://localhost:8000
```

## 📈 API Documentation

Interactive API documentation available at: `http://localhost:8000/docs`

## 🧪 Testing

```bash
# Run backend tests
cd backend
pytest -v

# Run frontend tests
cd frontend
npm run test

# Run engine tests
cd engine
pytest -v
```

## 🐛 Troubleshooting

### Database Issues
```bash
# Reset database
rm /e/Dev/major-proj/new_evua/evua/backend/storage/evua.db
# Restart backend to reinitialize
```

### Git Repo Issues
```bash
# Reset version control repos
rm -rf /e/Dev/major-proj/new_evua/evua/backend/storage/versions
# Reinitialize when processing next job
```

### Monaco Editor Not Loading
- Ensure `monaco-editor` is installed: `npm install monaco-editor`
- Check browser console for errors
- Clear browser cache

## 📝 Example Usage

### 1. Migrate PHP Files
```bash
curl -X POST http://localhost:8000/api/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_version": "5.6",
    "target_version": "8.0",
    "file_paths": ["/path/to/files"],
    "use_mock_ai": false
  }'

# Returns: {"job_id": "uuid", "status": "pending"}
```

### 2. Check Job Status & Risk
```bash
# Poll for job completion and risk assessment
curl http://localhost:8000/api/jobs/{job_id}

# Get risk summary
curl http://localhost:8000/api/risk/{job_id}/summary

# Get critical files needing AI review
curl http://localhost:8000/api/risk/{job_id}/critical
```

### 3. View Version History
```bash
# Get all versions
curl http://localhost:8000/api/versions/{job_id}/history

# Get diff between versions
curl "http://localhost:8000/api/versions/{job_id}/diff?from_commit=A&to_commit=B"
```

### 4. Review AI Suggestions
```bash
# Get AI verification results
curl http://localhost:8000/api/ai/verify/{job_id}/results

# Approve a suggestion
curl -X POST http://localhost:8000/api/ai/verify/{section_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"reviewer_notes": "Looks good"}'

# Apply the fix
curl -X POST http://localhost:8000/api/ai/verify/{section_id}/apply
```

## 🚀 Deployment

### Docker
```bash
docker-compose up -d
```

### Manual Deployment
```bash
# Install dependencies
pip install -r backend/requirements.txt
npm install --prefix frontend

# Build frontend
npm run build --prefix frontend

# Run backend
uvicorn app.main:app --port 8000 --workers 4
```

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please submit pull requests or issues.

## 📞 Support

For issues or questions:
1. Check API docs at `http://localhost:8000/docs`
2. Review logs in Docker output or terminal
3. Check database state in SQLite viewer
4. Inspect git repos in `/evua/backend/storage/versions/`
