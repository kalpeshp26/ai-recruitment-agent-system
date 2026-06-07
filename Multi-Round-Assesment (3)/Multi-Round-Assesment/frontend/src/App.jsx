import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import SessionRoute from './components/SessionRoute';
import SessionEntry from './pages/SessionEntry';
import ResumeUpload from './pages/ResumeUpload';
import HumanLikeInterview from './pages/HumanLikeInterview';
import InterviewReport from './pages/InterviewReport';
import AdminLogin from './pages/AdminLogin';
import AdminAnalyticsDashboard from './pages/AdminAnalyticsDashboard';
import AdminCandidateReports from './pages/AdminCandidateReports';
import AdminReview from './pages/AdminReview';
import AdminPools from './pages/AdminPools';
import AdminProctoringDashboard from './pages/AdminProctoringDashboard';
import AdminRoute from './components/AdminRoute';
import { ErrorBoundary } from './components/ErrorBoundary';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Main entry point - Session ID required */}
        <Route path="/" element={<SessionEntry />} />
        <Route path="/session" element={<SessionEntry />} />
        
        {/* Direct session link for Launch Interview button */}
        <Route path="/interview/session/:sessionId" element={<SessionEntry />} />
        
        {/* Admin routes */}
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route 
          path="/admin/dashboard" 
          element={
            <AdminRoute>
              <AdminAnalyticsDashboard />
            </AdminRoute>
          } 
        />
        <Route 
          path="/admin/analytics" 
          element={
            <AdminRoute>
              <AdminCandidateReports />
            </AdminRoute>
          } 
        />
        <Route 
          path="/admin/review" 
          element={
            <AdminRoute>
              <AdminReview />
            </AdminRoute>
          } 
        />
        <Route 
          path="/admin/pools"
          element={
            <AdminRoute>
              <AdminPools />
            </AdminRoute>
          }
        />
        <Route 
          path="/admin/proctoring" 
          element={
            <AdminRoute>
              <AdminProctoringDashboard />
            </AdminRoute>
          } 
        />
        
        {/* Interview flow - Session protected */}
        <Route
          path="/resume-upload"
          element={
            <SessionRoute>
              <ResumeUpload />
            </SessionRoute>
          }
        />
        <Route
          path="/interview"
          element={
            <SessionRoute>
              <HumanLikeInterview />
            </SessionRoute>
          }
        />
        <Route
          path="/interview/report/:interviewId"
          element={
            <SessionRoute>
              <InterviewReport />
            </SessionRoute>
          }
        />
        
        {/* Fallback to session entry */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
