// Minimal TTS service wrapper (frontend). Uses backend TTS endpoint when available
// or falls back to Web SpeechSynthesis for local dev.
(function () {
    const BACKEND_ORIGIN = 'http://127.0.0.1:8000';
    const INTERVIEW_API_BASE = `${BACKEND_ORIGIN}/api/v1/interview`;

    async function speak(text, opts = {}) {
        if (!text) return null;
        // Call backend /tts which returns a data URL for playback
        const resp = await fetch(`${INTERVIEW_API_BASE}/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, voice: opts.voice || 'default', sample_rate: opts.sample_rate || 16000 }),
        });
        if (!resp.ok) {
            const txt = await resp.text();
            throw new Error(txt || resp.statusText);
        }
        const payload = await resp.json();
        const audioUrl = payload.audio_url;
        if (!audioUrl) return null;
        // Play returned data URL or remote URL
        try {
            const audio = new Audio(audioUrl);
            await audio.play();
            return { played: true };
        } catch (err) {
            // Fallback to SpeechSynthesis
            if (window.speechSynthesis) {
                const utter = new SpeechSynthesisUtterance(text);
                utter.lang = opts.lang || 'en-US';
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(utter);
                return { played: 'synthesis' };
            }
            throw err;
        }
    }

    window.ttsService = { speak };
})();
