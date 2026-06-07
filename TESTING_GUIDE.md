# Frontend Testing Guide

## Quick Test Procedure

### 1. Test Resume Upload (Stage 2 - Candidate Intake)

**Steps:**
1. Navigate to "Candidate Intake" tab
2. Look for "Link to Job" dropdown - should show created jobs
3. Click on the upload zone OR drag a PDF/DOCX file
4. File picker should open
5. Select a resume file
6. Watch progress bar (20% → 60% → 100%)
7. Parsed resume data should appear below
8. Verify extracted: name, email, phone, skills, experience

**Expected Result:**
- Upload zone responds to clicks ✓
- Drag-and-drop works ✓
- Progress bar animates ✓
- Parse results display ✓
- Toast notification appears ✓

---

### 2. Test Job Dropdowns (All Stages)

**Steps:**
1. First create a job in Stage 1
2. Navigate to Stage 2 (Candidate Intake)
3. Check "Link to Job" dropdown - should list your job
4. Navigate to Stage 3 (Screening)
5. Check "Filter by Job" dropdown - should list your job
6. Navigate to Stage 4 (Outreach)
7. Check job filter - should list your job

**Expected Result:**
- All dropdowns populated with created jobs ✓
- Jobs appear across all stages ✓

---

### 3. Test Screening (Stage 3)

**Steps:**
1. Add at least one candidate (Stage 2)
2. Navigate to Stage 3 (Screening)
3. Optionally select a job from "Filter by Job"
4. Click "Run Screening" button
5. Watch button change to "Running..." with spinner
6. Wait for completion
7. Check stats cards update (Total, Screened, Shortlisted, etc.)
8. Check screening results table appears below

**Expected Result:**
- Button shows loading state ✓
- Screening executes successfully ✓
- Stats update ✓
- Results display in table ✓
- Toast notification appears ✓

---

### 4. Test Prescreening UI (Stage 5)

**Admin View:**
1. Navigate to Stage 5 (Prescreening)
2. Click "Admin View" button (should be highlighted)
3. Verify no UI overlap when scrolling down
4. Check filters are visible and functional

**Candidate View:**
1. Click "Candidate View (Demo)" button
2. Button should change to highlighted state
3. Admin view should hide
4. 6 demo questions should appear:
   - Professional background
   - Technical skills
   - Challenging project
   - Salary expectations
   - Interest in position
   - Career goals
5. Type in any textarea
6. Watch character counter update in real-time
7. Type enough characters to meet minimum
8. Check green "✓ Complete" indicator appears
9. Scroll down - UI should not break or overlap

**Expected Result:**
- Separate view buttons (not toggle) ✓
- Admin view shows session list ✓
- Candidate view shows 6 questions ✓
- Character counter works ✓
- No UI breaking on scroll ✓
- Visual indicators appear ✓

---

### 5. Test Data Flow Between Stages

**Full Pipeline Test:**
1. **Stage 1**: Create a job
2. **Stage 2**: Upload resume or add candidate manually (select the job)
3. **Stage 3**: Run screening
4. Verify candidate appears in screening results
5. Check status (shortlisted/rejected based on score)
6. **Stage 4**: Navigate to Outreach
7. Click "Refresh" - shortlisted candidates should appear
8. **Stage 5**: Navigate to Prescreening
9. Click "Refresh Prescreening Data"
10. Data should flow through all stages

**Expected Result:**
- Job created in Stage 1 visible in Stage 2 ✓
- Candidate from Stage 2 appears in Stage 3 ✓
- Shortlisted candidate appears in Stage 4 ✓
- Data persists across tab switches ✓

---

## Toast Notifications

Toast notifications should appear for:
- ✅ Resume upload success/failure
- ✅ Screening completion/failure
- ✅ Outreach send success/failure
- ✅ Data load failures
- ✅ Form validation errors

**Appearance:**
- Bottom right corner
- Auto-dismiss after 5 seconds
- Colored left border (green=success, red=error, orange=warning)
- Manual close button (×)
- Slide-in animation

---

## Visual Checks

### Upload Zone
- [ ] Gray dashed border when idle
- [ ] Blue border on hover
- [ ] Blue background on drag-over
- [ ] Upload icon visible
- [ ] Help text visible

### Buttons
- [ ] Admin View: Blue when active, gray when inactive
- [ ] Candidate View: Blue when active, gray when inactive
- [ ] Run Screening: Spinner animation when loading

### Prescreening Questions
- [ ] Numbered badges (1-6)
- [ ] White cards with shadow
- [ ] Textareas with focus effect (blue border + shadow)
- [ ] Character counter below each question
- [ ] Status indicators (green ✓ or orange warning)

---

## Common Issues & Solutions

### Issue: Upload zone not clickable
**Solution:** ✅ Fixed - now has proper click handler

### Issue: Job dropdowns empty
**Solution:** ✅ Fixed - loadJobsForSelect() populates all dropdowns

### Issue: Run Screening does nothing
**Solution:** ✅ Fixed - proper API call with loading state

### Issue: Prescreening UI overlaps on scroll
**Solution:** ✅ Fixed - proper overflow and padding CSS

### Issue: View buttons toggle instead of switch
**Solution:** ✅ Fixed - separate view selection

### Issue: No demo questions shown
**Solution:** ✅ Fixed - 6 questions with validation

---

## Browser Console

Open browser DevTools (F12) to check for:
- Network requests succeed (200 status)
- No JavaScript errors (red text)
- API responses contain data

**Useful Console Commands:**
```javascript
// Check state
console.log(state.jobs);
console.log(state.candidates);
console.log(state.stageData);

// Test toast notification
showToast('Test message', 'success');

// Manually trigger loads
loadJobs();
loadCandidates();
loadScreeningData();
```

---

## API Endpoints to Monitor

- `GET /api/intake/jobs` - Should return job list
- `POST /api/sourcing/resume/upload` - Should return parsed data
- `POST /api/screening/run` - Should return screening results
- `GET /api/screening/stats` - Should return statistics
- `GET /api/screening/candidates` - Should return candidate list

---

## Success Criteria

All features working correctly when:
1. ✅ Resume upload accepts files
2. ✅ Job dropdowns populate
3. ✅ Screening executes and shows results
4. ✅ Prescreening UI stable on scroll
5. ✅ View buttons work independently
6. ✅ Demo questions display with counters
7. ✅ Data flows between stages
8. ✅ Toast notifications appear
9. ✅ No JavaScript console errors
10. ✅ Loading states visible during operations
