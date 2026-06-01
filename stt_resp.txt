// Minimal STT service wrapper (frontend). Provides a mock transcribe() for
// local development. Real implementation would record audio and POST to backend.
(function () {
    const BACKEND_ORIGIN = 'http://127.0.0.1:8000';
    const INTERVIEW_API_BASE = `${BACKEND_ORIGIN}/api/v1/interview`;
    let mediaRecorder = null;
    let recordedChunks = [];
    let lastBlob = null;

    function isSupported() {
        return !!(navigator.mediaDevices && window.MediaRecorder);
    }

    async function startRecording() {
        if (!isSupported()) throw new Error('Recording not supported in this browser');
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recordedChunks = [];
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.addEventListener('dataavailable', (e) => { if (e.data && e.data.size) recordedChunks.push(e.data); });
        mediaRecorder.start();
        return true;
    }

    function stopRecording() {
        return new Promise((resolve, reject) => {
            if (!mediaRecorder) return resolve(null);
            mediaRecorder.addEventListener('stop', () => {
                lastBlob = new Blob(recordedChunks, { type: 'audio/webm' });
                // stop tracks
                try { mediaRecorder.stream.getTracks().forEach(t => t.stop()); } catch (e) {}
                mediaRecorder = null;
                resolve(lastBlob);
            });
            try { mediaRecorder.stop(); } catch (e) { resolve(null); }
        });
    }

    function playLastRecording() {
        if (!lastBlob) return null;
        const url = URL.createObjectURL(lastBlob);
        const audio = new Audio(url);
        audio.addEventListener('ended', () => { URL.revokeObjectURL(url); });
        audio.play();
        return audio;
    }

    async function transcribeLastRecording(sessionId) {
        if (!lastBlob) return '';
        const fd = new FormData();
        fd.append('file', lastBlob, `recording-${Date.now()}.webm`);
        const resp = await fetch(`${INTERVIEW_API_BASE}/stt`, { method: 'POST', body: fd });
        if (!resp.ok) {
            const txt = await resp.text();
            throw new Error(txt || resp.statusText);
        }
        const payload = await resp.json();
        return payload.transcript || '';
    }

    async function transcribeBlob(blob) {
        if (!blob) return '';
        const fd = new FormData();
        fd.append('file', blob, `recording-${Date.now()}.webm`);
        const resp = await fetch(`${INTERVIEW_API_BASE}/stt`, { method: 'POST', body: fd });
        if (!resp.ok) {
            const txt = await resp.text();
            throw new Error(txt || resp.statusText);
        }
        const payload = await resp.json();
        return payload.transcript || '';
    }

    window.sttService = { isSupported, startRecording, stopRecording, playLastRecording, transcribeLastRecording, transcribeBlob };
})();
