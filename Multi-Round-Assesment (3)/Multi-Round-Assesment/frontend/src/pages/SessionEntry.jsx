import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import './SessionEntry.css';

export default function SessionEntry() {
  const { sessionId: urlSessionId } = useParams();
  const [sessionId, setSessionId] = useState(urlSessionId || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  // Auto-validate if session ID in URL
  useEffect(() => {
    if (urlSessionId) {
      setSessionId(urlSessionId);
      handleValidation(urlSessionId);
    }
  }, [urlSessionId]);

  const handleValidation = async (sid) => {
    setError('');
    setLoading(true);

    try {
      // Validate session with backend
      const response = await axios.get(
        `http://localhost:8000/api/interview/session/validate/${sid}`
      );

      if (response.data.success && response.data.valid) {
        // Store session data in localStorage
        localStorage.setItem('interviewSessionId', sid);
        localStorage.setItem('candidateId', response.data.candidate_id);
        localStorage.setItem('jobId', response.data.job_id);
        
        // Auto-login details for candidate flow bypass
        localStorage.setItem('access_token', 'dummy_token_12345');
        const candidateName = response.data.candidate_name || 'Candidate';
        const candidateEmail = response.data.candidate_email || 'candidate@example.com';
        localStorage.setItem('user_name', candidateName);
        localStorage.setItem('full_name', candidateName);
        localStorage.setItem('user_email', candidateEmail);
        localStorage.setItem('email', candidateEmail);
        localStorage.setItem('user', JSON.stringify({ name: candidateName, email: candidateEmail }));
        
        // Navigate to resume upload
        navigate('/resume-upload');
      } else {
        setError(response.data.message || 'Invalid or expired session');
      }
    } catch (err) {
      console.error('Session validation error:', err);
      setError(
        err.response?.data?.detail || 
        'Invalid or expired session. Please check your Session ID.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    await handleValidation(sessionId);
  };

  return (
    <div className="session-entry-container">
      <div className="session-entry-card">
        <div className="session-entry-header">
          <h1>🎤 AI Interview Portal</h1>
          <p>Enter your Session ID to begin</p>
        </div>

        <form onSubmit={handleSubmit} className="session-entry-form">
          <div className="form-group">
            <label htmlFor="sessionId">Interview Session ID</label>
            <input
              type="text"
              id="sessionId"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value.trim())}
              placeholder="INT-2026-000123"
              required
              autoFocus
              disabled={loading}
              className="session-input"
            />
            <small>Enter the Session ID from your invitation email</small>
          </div>

          {error && (
            <div className="error-message">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
              </svg>
              {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={loading || !sessionId}
            className="start-interview-btn"
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Validating...
              </>
            ) : (
              'Start Interview →'
            )}
          </button>
        </form>

        <div className="session-entry-footer">
          <p>Don't have a Session ID?</p>
          <small>
            Complete the prescreening assessment first. You'll receive your 
            Session ID via email once approved.
          </small>
        </div>
      </div>
    </div>
  );
}
