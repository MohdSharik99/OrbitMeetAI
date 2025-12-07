# Transcript to MongoDB Flow Review

## ✅ Flow Overview

Your `transcript_to_mongo.py` script implements a **file watcher** that:
1. **Monitors** `SampleData/Transcripts` directory for new transcript files
2. **Uploads** new files to MongoDB (`OMNI_MEET_DB.Raw_Transcripts`)
3. **Runs hourly** via APScheduler to check for new files
4. **Tracks processed files** to avoid duplicates

This works in conjunction with your backend scheduler (`src/backend/scheduler.py`) which:
1. **Finds unprocessed meetings** in MongoDB (where `processed: False`)
2. **Runs the orchestrator** on them
3. **Marks them as processed** after completion

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────┐
│ 1. Add transcript file to      │
│    SampleData/Transcripts/     │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 2. transcript_to_mongo.py       │
│    (runs every hour)            │
│    - Scans directory            │
│    - Uploads to MongoDB         │
│    - DB: OMNI_MEET_DB           │
│    - Collection: Raw_Transcripts│
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 3. Backend Scheduler            │
│    (runs every hour)            │
│    - Finds unprocessed meetings │
│    - Runs orchestrator          │
│    - Marks as processed         │
└─────────────────────────────────┘
```

## ⚠️ Issues Found & Fixes

### 1. **Database Name Mismatch**
- **You mentioned**: `OMNIMEET_DB` (no underscore)
- **Code uses**: `OMNI_MEET_DB` (with underscore)
- **Status**: ✅ Code is consistent across all files
- **Action**: If your actual MongoDB database is `OMNIMEET_DB`, you need to update all references

### 2. **Directory Path**
- **You mentioned**: `sampleData/Transcript` (lowercase, singular)
- **Code uses**: `SampleData/Transcripts` (capital S, plural)
- **Status**: ✅ Actual directory exists as `SampleData/Transcripts`
- **Action**: No change needed - code matches actual directory

### 3. **Async Execution Pattern**
- **Issue**: `asyncio.get_event_loop().run_forever()` may not work correctly
- **Fix**: Changed to use `time.sleep()` loop (simpler and more reliable)
- **Status**: ✅ Fixed

## 📋 How to Run

### Option 1: Standalone Service (Recommended for Production)

Run `transcript_to_mongo.py` as a separate background service:

```bash
# Activate virtual environment
.venv/Scripts/activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# Run the script
python transcript_to_mongo.py
```

**What it does:**
- Starts immediately and checks for new files
- Runs a check every hour (at :00 minutes)
- Keeps running until you press `Ctrl+C`
- Logs all activity to console

### Option 2: Manual Trigger (For Testing)

You can also trigger a manual check programmatically:

```python
from transcript_to_mongo import run_manual_check
import asyncio

# Run a manual check
asyncio.run(run_manual_check())
```

### Option 3: Integrate with FastAPI Backend

You could integrate this into your FastAPI backend's lifespan, but it's **recommended to keep it separate** because:
- It's a file system watcher (different concern)
- Backend scheduler handles processing (different concern)
- Separation of concerns = better maintainability

## 🔍 Verification Steps

1. **Check Directory**:
   ```bash
   ls SampleData/Transcripts/
   ```

2. **Check MongoDB**:
   - Connect to MongoDB Atlas
   - Verify database: `OMNI_MEET_DB`
   - Verify collection: `Raw_Transcripts`
   - Check if documents are being created

3. **Test Flow**:
   - Add a new `.docx` file to `SampleData/Transcripts/`
   - Wait for next hourly check (or trigger manually)
   - Verify file appears in MongoDB
   - Check backend scheduler processes it

## 🐛 Potential Issues & Solutions

### Issue: Files Not Being Detected
**Solution**: 
- Check file extensions (must be `.txt`, `.docx`, or `.pdf`)
- Verify `SampleData/Transcripts` path is correct
- Check file permissions

### Issue: Duplicate Uploads
**Solution**: 
- Script checks `project_key` existence before uploading
- Uses fuzzy matching (90% similarity) to detect duplicates
- Tracks processed files in memory

### Issue: MongoDB Connection Errors
**Solution**:
- Verify `MONGO_URI` in `.env` file
- Check MongoDB Atlas Network Access (IP whitelist)
- Verify SSL/TLS settings

### Issue: Script Stops Running
**Solution**:
- Use a process manager (e.g., `systemd`, `supervisord`, or Windows Task Scheduler)
- Or run it as a background service with proper logging

## 📝 Recommendations

1. **Add File Watching (Optional Enhancement)**:
   Instead of polling every hour, you could use `watchdog` library for real-time file detection:
   ```python
   from watchdog.observers import Observer
   from watchdog.events import FileSystemEventHandler
   ```

2. **Add Logging to File**:
   Currently logs to console. Consider adding file logging:
   ```python
   logger.add("transcript_upload.log", rotation="10 MB")
   ```

3. **Add Error Recovery**:
   If upload fails, retry logic could be added

4. **Add Health Check Endpoint** (if integrated):
   Could add a `/health` endpoint to check if service is running

## ✅ Summary

**Your flow is correct!** The script will:
- ✅ Monitor `SampleData/Transcripts` directory
- ✅ Upload new transcripts to MongoDB
- ✅ Avoid duplicates
- ✅ Run automatically every hour

**To run it:**
```bash
python transcript_to_mongo.py
```

The script will keep running and checking for new files every hour. Press `Ctrl+C` to stop it.

