// Minimal STT service wrapper (frontend). Provides a mock transcribe() for
// local development. Real implementation would record audio and POST to backend.
(function () {
    const BACKEND_ORIGIN = 'http://127.0.0.1:8000';
    const INTERVIEW_API_BASE = `${BACKEND_ORIGIN}/api/v1/interview`;
    let mediaRecorder = null;
    let recordedChunks = [];
    let lastOriginalBlob = null; // raw container (webm)
    let lastWavBlob = null; // converted 16kHz WAV

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
            mediaRecorder.addEventListener('stop', async () => {
                lastOriginalBlob = new Blob(recordedChunks, { type: 'audio/webm' });
                // stop tracks
                try { mediaRecorder.stream.getTracks().forEach(t => t.stop()); } catch (e) {}
                mediaRecorder = null;
                try {
                    lastWavBlob = await convertBlobToWav16k(lastOriginalBlob);
                } catch (e) {
                    // conversion failed — fall back to original blob
                    lastWavBlob = lastOriginalBlob;
                }
                resolve(lastWavBlob || lastOriginalBlob);
            });
            try { mediaRecorder.stop(); } catch (e) { resolve(null); }
        });
    }

    function playLastRecording() {
        const blob = lastWavBlob || lastOriginalBlob;
        if (!blob) return null;
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.addEventListener('ended', () => { URL.revokeObjectURL(url); });
        audio.play();
        return audio;
    }

    async function transcribeLastRecording(sessionId) {
        const blob = lastWavBlob || lastOriginalBlob;
        if (!blob) return '';
        const fd = new FormData();
        fd.append('file', blob, `recording-${Date.now()}.wav`);
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
        // convert arbitrary blobs to WAV 16kHz when possible
        let sendBlob = blob;
        try { sendBlob = await convertBlobToWav16k(blob); } catch (e) { sendBlob = blob; }
        const fd = new FormData();
        fd.append('file', sendBlob, `recording-${Date.now()}.wav`);
        const resp = await fetch(`${INTERVIEW_API_BASE}/stt`, { method: 'POST', body: fd });
        if (!resp.ok) {
            const txt = await resp.text();
            throw new Error(txt || resp.statusText);
        }
        const payload = await resp.json();
        return payload.transcript || '';
    }

    // Convert arbitrary audio Blob (webm, ogg, etc.) to 16kHz PCM WAV Blob
    async function convertBlobToWav16k(blob) {
        if (!blob) throw new Error('No blob to convert');
        const arrayBuffer = await blob.arrayBuffer();
        const decodeCtx = new (window.AudioContext || window.webkitAudioContext)();
        let audioBuffer;
        try {
            audioBuffer = await decodeCtx.decodeAudioData(arrayBuffer.slice(0));
        } finally {
            try { decodeCtx.close(); } catch (e) {}
        }

        const numChannels = Math.min(1, audioBuffer.numberOfChannels);
        const duration = audioBuffer.duration;
        const sampleRate = 16000;
        const frameCount = Math.ceil(duration * sampleRate);

        const offlineCtx = new (window.OfflineAudioContext || window.webkitOfflineAudioContext)(numChannels, frameCount, sampleRate);
        const bufferSource = offlineCtx.createBufferSource();
        bufferSource.buffer = audioBuffer;
        bufferSource.connect(offlineCtx.destination);
        bufferSource.start(0);
        const rendered = await offlineCtx.startRendering();

        const channelData = rendered.getChannelData(0);

        // 16-bit PCM
        const wavBuffer = encodeWAV(channelData, sampleRate, numChannels);
        return new Blob([wavBuffer], { type: 'audio/wav' });
    }

    function encodeWAV(samples, sampleRate, numChannels) {
        const bytesPerSample = 2;
        const blockAlign = numChannels * bytesPerSample;
        const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
        const view = new DataView(buffer);

        /* RIFF identifier */ writeString(view, 0, 'RIFF');
        /* file length */ view.setUint32(4, 36 + samples.length * bytesPerSample, true);
        /* RIFF type */ writeString(view, 8, 'WAVE');
        /* format chunk identifier */ writeString(view, 12, 'fmt ');
        /* format chunk length */ view.setUint32(16, 16, true);
        /* sample format (raw) */ view.setUint16(20, 1, true);
        /* channel count */ view.setUint16(22, numChannels, true);
        /* sample rate */ view.setUint32(24, sampleRate, true);
        /* byte rate (sampleRate * blockAlign) */ view.setUint32(28, sampleRate * blockAlign, true);
        /* block align (channelCount * bytesPerSample) */ view.setUint16(32, blockAlign, true);
        /* bits per sample */ view.setUint16(34, 8 * bytesPerSample, true);
        /* data chunk identifier */ writeString(view, 36, 'data');
        /* data chunk length */ view.setUint32(40, samples.length * bytesPerSample, true);

        // write PCM samples
        let offset = 44;
        for (let i = 0; i < samples.length; i++, offset += 2) {
            const s = Math.max(-1, Math.min(1, samples[i]));
            view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
        return view;
    }

    function writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    window.sttService = { isSupported, startRecording, stopRecording, playLastRecording, transcribeLastRecording, transcribeBlob };
})();
