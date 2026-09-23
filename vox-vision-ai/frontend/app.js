/**
 * VoxVision AI - Frontend Logic (Step 5: Voice Pipeline with TTS)
 * Features: Real-time WebSocket chat, Groq Whisper STT, gTTS Text-to-Speech synthesis,
 * auto voice playback on microphone prompts, interactive listen buttons on assistant bubbles.
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const statusDot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');
  const latencyTag = document.getElementById('latency-tag');
  const chatMessages = document.getElementById('chat-messages');
  const emptyState = document.getElementById('empty-state');
  const chatViewport = document.getElementById('chat-viewport');
  const messageInput = document.getElementById('message-input');
  const charCounter = document.getElementById('char-counter');
  const btnSend = document.getElementById('btn-send');
  const btnClearChat = document.getElementById('btn-clear-chat');

  // Tool buttons
  const btnMic = document.getElementById('btn-mic');
  const btnImage = document.getElementById('btn-image');
  const btnCamera = document.getElementById('btn-camera');
  const previewSpeech = document.getElementById('preview-speech');
  const previewTTS = document.getElementById('preview-tts');

  // Modal elements
  const featureModal = document.getElementById('feature-modal');
  const modalClose = document.getElementById('modal-close');
  const modalTitle = document.getElementById('modal-title');
  const modalSubtitle = document.getElementById('modal-subtitle');
  const modalDescription = document.getElementById('modal-description');
  const modalChecklist = document.getElementById('modal-checklist');
  const modalIcon = document.getElementById('modal-icon');
  const modalActionBtn = document.getElementById('modal-action-btn');
  const toastContainer = document.getElementById('toast-container');

  // State flag for auto-playing voice response on microphone prompts
  let shouldAutoPlayVoice = false;

  // 1. Text-to-Speech Audio Player Manager
  class VoicePlayer {
    constructor() {
      this.currentAudio = null;
      this.currentButton = null;
    }

    async playText(text, buttonElement) {
      // Toggle off if currently playing on the same button
      if (this.currentButton === buttonElement && this.currentAudio && !this.currentAudio.paused) {
        this.stop();
        return;
      }

      this.stop();

      if (!text || !text.trim()) return;

      if (buttonElement) {
        buttonElement.classList.add('speaking');
        const labelSpan = buttonElement.querySelector('span');
        if (labelSpan) labelSpan.textContent = 'Speaking...';
      }

      this.currentButton = buttonElement;

      try {
        const response = await fetch('/api/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const blob = await response.blob();
        const audioUrl = URL.createObjectURL(blob);
        this.currentAudio = new Audio(audioUrl);

        this.currentAudio.onended = () => {
          this.resetButtonUI();
          URL.revokeObjectURL(audioUrl);
        };

        this.currentAudio.onerror = (e) => {
          console.warn('[VoxVision TTS] Playback error:', e);
          this.resetButtonUI();
          showToast('⚠️ Audio playback failed.');
          URL.revokeObjectURL(audioUrl);
        };

        await this.currentAudio.play();
      } catch (err) {
        console.error('[VoxVision TTS Error]:', err);
        this.resetButtonUI();
        showToast(`❌ TTS Error: ${err.message}`);
      }
    }

    stop() {
      if (this.currentAudio) {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
        this.currentAudio = null;
      }
      this.resetButtonUI();
    }

    resetButtonUI() {
      if (this.currentButton) {
        this.currentButton.classList.remove('speaking');
        const labelSpan = this.currentButton.querySelector('span');
        if (labelSpan) labelSpan.textContent = 'Listen';
        this.currentButton = null;
      }
    }
  }

  const voicePlayer = new VoicePlayer();

  // 2. WebSocket Connection Manager
  class WebSocketManager {
    constructor() {
      this.socket = null;
      this.reconnectAttempts = 0;
      this.maxReconnectDelay = 10000;
      this.pingInterval = null;
      this.pingStartTime = 0;
      this.pendingTypingIndicator = null;
      this.isManuallyClosed = false;

      this.initConnection();
    }

    getWebSocketUrl() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host || '127.0.0.1:8000';
      return `${protocol}//${host}/ws/chat`;
    }

    initConnection() {
      const url = this.getWebSocketUrl();
      this.updateStatusUI('connecting', 'Connecting...');

      try {
        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
          this.reconnectAttempts = 0;
          this.updateStatusUI('online', 'Connected (WS)');
          this.startPingHeartbeat();
        };

        this.socket.onmessage = (event) => {
          this.handleIncomingMessage(event);
        };

        this.socket.onerror = (error) => {
          console.warn('[VoxVision WS] Connection error:', error);
          this.updateStatusUI('offline', 'Error');
        };

        this.socket.onclose = (event) => {
          this.stopPingHeartbeat();
          if (!this.isManuallyClosed) {
            this.scheduleReconnect();
          } else {
            this.updateStatusUI('offline', 'Disconnected');
          }
        };
      } catch (err) {
        console.error('[VoxVision WS] Initialization failed:', err);
        this.scheduleReconnect();
      }
    }

    scheduleReconnect() {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(1.8, this.reconnectAttempts - 1), this.maxReconnectDelay);
      const seconds = Math.round(delay / 1000);

      this.updateStatusUI('reconnecting', `Reconnecting in ${seconds}s...`);

      setTimeout(() => {
        if (!this.isConnected()) {
          this.initConnection();
        }
      }, delay);
    }

    startPingHeartbeat() {
      this.stopPingHeartbeat();
      this.pingInterval = setInterval(() => {
        if (this.isConnected()) {
          this.pingStartTime = performance.now();
          this.sendJSON({ type: 'ping' });
        }
      }, 12000);
    }

    stopPingHeartbeat() {
      if (this.pingInterval) {
        clearInterval(this.pingInterval);
        this.pingInterval = null;
      }
    }

    isConnected() {
      return this.socket && this.socket.readyState === WebSocket.OPEN;
    }

    sendJSON(payload) {
      if (this.isConnected()) {
        this.socket.send(JSON.stringify(payload));
        return true;
      }
      return false;
    }

    updateStatusUI(state, label, latency = '--ms') {
      statusDot.className = `status-dot ${state}`;
      statusText.textContent = label;
      if (latency !== undefined) {
        latencyTag.textContent = latency;
      }
    }

    handleIncomingMessage(event) {
      try {
        const data = JSON.parse(event.data);

        // Pong response for latency calculation
        if (data.type === 'pong') {
          const latency = Math.round(performance.now() - this.pingStartTime);
          latencyTag.textContent = `${latency}ms`;
          return;
        }

        // Connection acknowledgment
        if (data.type === 'connection_ack') {
          console.log('[VoxVision WS] Connected:', data.message);
          return;
        }

        // Chat response frame
        if (data.type === 'chat_response') {
          if (this.pendingTypingIndicator) {
            this.pendingTypingIndicator.remove();
            this.pendingTypingIndicator = null;
          }
          const providerTag = data.provider ? ` (${data.provider})` : '';
          const msgRow = appendMessageBubble('assistant', data.reply, getFormattedTime(), providerTag);
          btnSend.disabled = false;

          // Auto-play voice response if prompt came from microphone
          if (shouldAutoPlayVoice) {
            shouldAutoPlayVoice = false;
            const listenBtn = msgRow.querySelector('.btn-listen-msg');
            voicePlayer.playText(data.reply, listenBtn);
          }
          return;
        }

        // Error payload
        if (data.type === 'error') {
          if (this.pendingTypingIndicator) {
            this.pendingTypingIndicator.remove();
            this.pendingTypingIndicator = null;
          }
          appendMessageBubble('assistant', `⚠️ ${data.message}`, getFormattedTime());
          showToast(`Backend error: ${data.message}`);
          btnSend.disabled = false;
          shouldAutoPlayVoice = false;
        }
      } catch (err) {
        console.error('[VoxVision WS] Failed to parse message frame:', err);
      }
    }
  }

  // Initialize WebSocket Manager Instance
  const wsManager = new WebSocketManager();

  // 3. Input Auto-Resize & Character Counter
  messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = `${Math.min(messageInput.scrollHeight, 140)}px`;
    const count = messageInput.value.length;
    charCounter.textContent = `${count} / 2000`;
  });

  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  btnSend.addEventListener('click', sendMessage);

  // Clear Chat Listener
  btnClearChat.addEventListener('click', () => {
    voicePlayer.stop();
    chatMessages.innerHTML = '';
    if (emptyState) {
      emptyState.style.display = 'flex';
      chatMessages.appendChild(emptyState);
    }
    showToast('Conversation cleared.');
  });

  // 4. Quick Suggestion Pills
  document.querySelectorAll('.pill-btn').forEach(pill => {
    pill.addEventListener('click', () => {
      const promptText = pill.getAttribute('data-prompt');
      if (promptText) {
        messageInput.value = promptText;
        messageInput.style.height = 'auto';
        charCounter.textContent = `${promptText.length} / 2000`;
        sendMessage();
      }
    });
  });

  // 5. Send Message Logic
  function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;

    if (!wsManager.isConnected()) {
      showToast('WebSocket disconnected. Reconnecting to server...');
      wsManager.initConnection();
      return;
    }

    // Hide empty state if present
    if (emptyState && emptyState.parentNode === chatMessages) {
      emptyState.style.display = 'none';
    }

    const timestamp = getFormattedTime();

    // Render User Message Bubble
    appendMessageBubble('user', text, timestamp);

    // Reset Input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    charCounter.textContent = '0 / 2000';
    btnSend.disabled = true;

    // Show typing indicator
    wsManager.pendingTypingIndicator = appendTypingIndicator();
    scrollToBottom();

    // Send payload over WebSocket
    const sent = wsManager.sendJSON({
      type: 'chat_message',
      message: text,
      session_id: 'default'
    });

    if (!sent) {
      if (wsManager.pendingTypingIndicator) {
        wsManager.pendingTypingIndicator.remove();
        wsManager.pendingTypingIndicator = null;
      }
      appendMessageBubble('assistant', 'Failed to transmit message over WebSocket.', getFormattedTime());
      btnSend.disabled = false;
      shouldAutoPlayVoice = false;
    }
  }

  // 6. Message Renderer with Listen & Copy Buttons
  function appendMessageBubble(role, content, time, metaTag = '') {
    const row = document.createElement('div');
    row.className = `msg-row ${role}`;

    const avatarText = role === 'user' ? 'U' : 'VV';
    const formattedContent = formatMessageText(content);

    const actionButtonsHTML = role === 'assistant' 
      ? `<button class="btn-listen-msg" aria-label="Listen to voice">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>
          <span>Listen</span>
         </button>
         <button class="btn-copy-msg" aria-label="Copy text">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          <span>Copy</span>
         </button>`
      : '';

    row.innerHTML = `
      <div class="msg-avatar">${avatarText}</div>
      <div class="msg-content-wrapper">
        <div class="msg-bubble">${formattedContent}</div>
        <div class="msg-meta">
          <span class="msg-time">${time}${escapeHtml(metaTag)}</span>
          ${actionButtonsHTML}
        </div>
      </div>
    `;

    chatMessages.appendChild(row);

    // Attach Event Handlers for Assistant Bubbles
    if (role === 'assistant') {
      const copyBtn = row.querySelector('.btn-copy-msg');
      if (copyBtn) {
        copyBtn.addEventListener('click', () => {
          navigator.clipboard.writeText(content);
          const span = copyBtn.querySelector('span');
          span.textContent = 'Copied!';
          setTimeout(() => { span.textContent = 'Copy'; }, 2000);
        });
      }

      const listenBtn = row.querySelector('.btn-listen-msg');
      if (listenBtn) {
        listenBtn.addEventListener('click', () => {
          voicePlayer.playText(content, listenBtn);
        });
      }
    }

    scrollToBottom();
    return row;
  }

  function appendTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'msg-row assistant thinking-row';
    row.innerHTML = `
      <div class="msg-avatar">VV</div>
      <div class="msg-content-wrapper">
        <div class="msg-bubble thinking-bubble">
          <span class="thinking-dots">
            <span class="dot"></span>
            <span class="dot"></span>
            <span class="dot"></span>
          </span>
          <span class="thinking-text">VoxVision AI is reasoning...</span>
        </div>
      </div>
    `;
    chatMessages.appendChild(row);
    return row;
  }

  function scrollToBottom() {
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  function getFormattedTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function formatMessageText(text) {
    if (!text) return '';
    let formatted = escapeHtml(text);
    
    // Code blocks ```code```
    formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre class="code-block"><code>$1</code></pre>');
    // Inline code `code`
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold **text**
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Italic *text*
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');
    return formatted;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // 7. Interactive Feature Preview Roadmap Modal
  const featureSpecs = {
    speech: {
      title: 'Speech Engine (Groq Whisper)',
      subtitle: 'Step 4 Active',
      icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>',
      description: 'The VoxVision speech pipeline transcribes voice prompts via Groq Whisper large-v3-turbo API with sub-second latency.',
      checklist: [
        'Browser MediaRecorder microphone audio capture',
        'FastAPI backend endpoint /api/stt',
        'Groq Whisper large-v3-turbo API integration',
        'Automated transmission to LLM chat pipeline'
      ]
    },
    tts: {
      title: 'TTS Voice Synthesis Engine',
      subtitle: 'Step 5 Active',
      icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>',
      description: 'The Text-to-Speech synthesis engine converts AI responses into natural MP3 voice audio with Markdown formatting sanitization.',
      checklist: [
        'FastAPI backend endpoint /api/tts',
        'Google Text-to-Speech (gTTS) audio synthesis',
        'Markdown code block & symbol sanitization',
        'Automated voice playback for microphone prompts'
      ]
    },
    vision: {
      title: 'Computer Vision Analysis',
      subtitle: 'Step 6 Roadmap',
      icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>',
      description: 'The vision engine enables multimodal document scanning, image feature extraction, and visual reasoning.',
      checklist: [
        'Image drag-and-drop & file selector upload',
        'Multimodal Vision LLM prompt processing',
        'OCR text extraction & chart recognition',
        'Client-side image compression & preview'
      ]
    },
    camera: {
      title: 'Live Camera Stream Pipeline',
      subtitle: 'Step 7 Roadmap',
      icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
      description: 'Real-time webcam video stream integration for continuous spatial awareness and live scene description.',
      checklist: [
        'HTML5 getUserMedia video stream access',
        'Frame sampling rate configuration (1-5 fps)',
        'Real-time object & boundary detection',
        'Interactive camera preview modal widget'
      ]
    }
  };

  function openFeatureModal(key) {
    const spec = featureSpecs[key];
    if (!spec) return;

    modalIcon.innerHTML = spec.icon;
    modalTitle.textContent = spec.title;
    modalSubtitle.textContent = spec.subtitle;
    modalDescription.textContent = spec.description;

    modalChecklist.innerHTML = spec.checklist
      .map(item => `
        <div class="check-item">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
          <span>${item}</span>
        </div>
      `).join('');

    featureModal.classList.add('active');
    featureModal.setAttribute('aria-hidden', 'false');
  }

  function closeModal() {
    featureModal.classList.remove('active');
    featureModal.setAttribute('aria-hidden', 'true');
  }

  // Trigger bindings
  if (btnImage) btnImage.addEventListener('click', () => openFeatureModal('vision'));
  if (btnCamera) btnCamera.addEventListener('click', () => openFeatureModal('camera'));
  if (previewSpeech) previewSpeech.addEventListener('click', () => openFeatureModal('speech'));
  if (previewTTS) previewTTS.addEventListener('click', () => openFeatureModal('tts'));

  // 8. Voice Recording Manager (Step 4 Speech-to-Text via Groq Whisper API)
  class VoiceRecorder {
    constructor() {
      this.mediaRecorder = null;
      this.audioChunks = [];
      this.isRecording = false;
      this.stream = null;
      this.micLabel = document.getElementById('mic-label');
    }

    async toggleRecording() {
      if (this.isRecording) {
        this.stopRecording();
      } else {
        await this.startRecording();
      }
    }

    async startRecording() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showToast('Browser does not support microphone recording.');
        return;
      }

      try {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.audioChunks = [];
        
        let mimeType = 'audio/webm';
        if (!MediaRecorder.isTypeSupported('audio/webm')) {
          if (MediaRecorder.isTypeSupported('audio/ogg')) mimeType = 'audio/ogg';
          else if (MediaRecorder.isTypeSupported('audio/mp4')) mimeType = 'audio/mp4';
          else mimeType = '';
        }

        const options = mimeType ? { mimeType } : {};
        this.mediaRecorder = new MediaRecorder(this.stream, options);

        this.mediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            this.audioChunks.push(e.data);
          }
        };

        this.mediaRecorder.onstop = async () => {
          this.setRecordingState(false);
          const audioBlob = new Blob(this.audioChunks, { type: this.mediaRecorder.mimeType || 'audio/webm' });
          await this.uploadAudio(audioBlob);
          this.cleanupStream();
        };

        this.mediaRecorder.start();
        this.isRecording = true;
        this.setRecordingState(true);
        showToast('🎙️ Recording voice prompt... Click Stop to finish.');

      } catch (err) {
        console.warn('[VoxVision Mic] Permission/hardware error:', err);
        this.setRecordingState(false);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          showToast('⚠️ Microphone access denied. Please allow microphone permissions.');
        } else {
          showToast(`⚠️ Microphone error: ${err.message || 'Unable to access microphone'}`);
        }
      }
    }

    stopRecording() {
      if (this.mediaRecorder && this.isRecording) {
        this.mediaRecorder.stop();
        this.isRecording = false;
        showToast('⚡ Processing audio recording...');
      }
    }

    cleanupStream() {
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
        this.stream = null;
      }
    }

    setRecordingState(active) {
      if (active) {
        btnMic.classList.add('recording');
        if (this.micLabel) this.micLabel.textContent = 'Stop';
      } else {
        btnMic.classList.remove('recording');
        if (this.micLabel) this.micLabel.textContent = 'Voice';
      }
    }

    async uploadAudio(audioBlob) {
      if (audioBlob.size === 0) {
        showToast('⚠️ Empty audio recorded.');
        return;
      }

      showToast('Transcribing audio with Groq Whisper...');
      const formData = new FormData();
      formData.append('file', audioBlob, 'speech.webm');

      try {
        const response = await fetch('/api/stt', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        if (data.status === 'success' || data.text) {
          const transcribedText = data.text;
          if (transcribedText) {
            messageInput.value = transcribedText;
            messageInput.style.height = 'auto';
            charCounter.textContent = `${transcribedText.length} / 2000`;
            showToast('Voice transcribed! Sending to AI...');
            shouldAutoPlayVoice = true; // Auto play synthesized voice response
            sendMessage();
          } else {
            showToast('⚠️ No speech detected in audio.');
          }
        } else {
          showToast(`⚠️ STT Warning: ${data.message || 'Speech-to-text failed.'}`);
        }
      } catch (err) {
        console.error('[VoxVision STT Error]:', err);
        showToast(`❌ STT Error: ${err.message}`);
      }
    }
  }

  const voiceRecorder = new VoiceRecorder();
  if (btnMic) {
    btnMic.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      voiceRecorder.toggleRecording();
    };
  }

  modalClose.addEventListener('click', closeModal);
  modalActionBtn.addEventListener('click', closeModal);
  featureModal.addEventListener('click', (e) => {
    if (e.target === featureModal) closeModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && featureModal.classList.contains('active')) {
      closeModal();
    }
  });

  // Toast Banner Helper
  function showToast(message) {
    toastContainer.innerHTML = '';
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
      <svg class="toast-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
      <span>${message}</span>
    `;
    toastContainer.appendChild(toast);
    setTimeout(() => { if (toast.parentNode) toast.remove(); }, 2800);
  }
});
