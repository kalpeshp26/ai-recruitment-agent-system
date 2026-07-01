import { Navigate } from 'react-router-dom';

/**
 * SessionRoute - Protects interview routes
 * Requires valid session ID in localStorage
 */
export default function SessionRoute({ children }) {
  const sessionId = localStorage.getItem('interviewSessionId');
  
  if (!sessionId) {
    // Redirect to session entry if no session
    return <Navigate to="/" replace />;
  }
  
  return children;
}
