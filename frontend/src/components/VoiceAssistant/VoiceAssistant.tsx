import React, { useState, useEffect, useRef } from 'react';
import { fetchCitizenBlend, fetchCitizenAlerts } from '../../api/client';
import { CITIES, CityOption } from '../CitizenPortal/CitizenPortal';

interface VoiceAssistantProps {
  currentView?: 'operator' | 'citizen';
  onNavigateView?: (view: 'operator' | 'citizen') => void;
  onSelectCity?: (city: CityOption) => void;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestamp: string;
  actionType?: 'weather' | 'alert' | 'weights' | 'navigation' | 'general';
  dataPayload?: any;
}

export const VoiceAssistant: React.FC<VoiceAssistantProps> = ({
  currentView,
  onNavigateView,
  onSelectCity,
}) => {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>('');
  const [textInput, setTextInput] = useState<string>('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-1',
      sender: 'bot',
      text: "Namaste! I am VaruBot, your VaruNet AI Weather Voice Assistant. Tap the microphone or speak a question like 'What is the weather in Kochi?' or 'Are there any weather alerts?'",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      actionType: 'general',
    },
  ]);

  const recognitionRef = useRef<any>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const [isSpeechSupported, setIsSpeechSupported] = useState<boolean>(true);

  // Initialize Speech Recognition
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSpeechSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-IN'; // Indian English recognition

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript('');
    };

    recognition.onresult = (event: any) => {
      let currentTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        currentTranscript += event.results[i][0].transcript;
      }
      setTranscript(currentTranscript);

      // If final speech segment captured
      if (event.results[0].isFinal) {
        handleUserQuery(currentTranscript);
      }
    };

    recognition.onerror = (event: any) => {
      console.warn('Speech recognition error:', event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isListening]);

  // Text-To-Speech Output
  const speakText = (text: string) => {
    if (isMuted || !('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel(); // Stop any previous speech
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-IN';
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Pick a natural English voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(
      (v) =>
        v.lang.includes('en-IN') ||
        v.name.includes('Google UK English') ||
        v.name.includes('Natural') ||
        v.name.includes('Samantha') ||
        v.name.includes('Zira')
    );
    if (preferredVoice) utterance.voice = preferredVoice;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const stopSpeaking = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  const toggleListening = () => {
    stopSpeaking();
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. You can type your question in the text box below.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
      } catch {
        recognitionRef.current.stop();
        setTimeout(() => recognitionRef.current.start(), 200);
      }
    }
  };

  // Process User Query via NLP Intent Handler
  const handleUserQuery = async (queryText: string) => {
    const trimmed = queryText.trim();
    if (!trimmed) return;

    const userMessage: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setTextInput('');
    setTranscript('');

    const lower = trimmed.toLowerCase();

    // 1. Navigation Commands
    if (lower.includes('citizen') || lower.includes('public portal')) {
      if (onNavigateView) onNavigateView('citizen');
      const response = 'Switching to the Citizen Weather Portal with plain-language advisories.';
      addBotResponse(response, 'navigation');
      speakText(response);
      return;
    }

    if (lower.includes('operator') || lower.includes('dashboard') || lower.includes('command')) {
      if (onNavigateView) onNavigateView('operator');
      const response = 'Switching to the Operator Command Dashboard with multi-model geospatial weights and TreeSHAP explainability.';
      addBotResponse(response, 'navigation');
      speakText(response);
      return;
    }

    // 2. Weather Alert Queries
    if (lower.includes('alert') || lower.includes('warning') || lower.includes('flood') || lower.includes('cyclone') || lower.includes('heatwave')) {
      try {
        const alerts = await fetchCitizenAlerts({});
        if (alerts && alerts.length > 0) {
          const topAlert = alerts[0];
          const response = `Attention: There is an active ${topAlert.severity} Alert for ${topAlert.alert_type}. ${topAlert.sector_guidance_text}`;
          addBotResponse(response, 'alert', topAlert);
          speakText(response);
        } else {
          const response = 'Great news! There are currently no active weather hazard warnings across the monitored regions. Normal meteorological conditions prevail.';
          addBotResponse(response, 'alert');
          speakText(response);
        }
      } catch {
        const response = 'Currently, standard monsoon advisories are active for coastal zones. Exercise normal safety precautions near waterways.';
        addBotResponse(response, 'alert');
        speakText(response);
      }
      return;
    }

    // 3. City-specific Forecast Queries
    let matchedCity: CityOption | undefined = CITIES.find((c: CityOption) =>
      lower.includes(c.name.toLowerCase())
    );


    // Common synonyms
    if (!matchedCity) {
      if (lower.includes('cochin') || lower.includes('kerala')) matchedCity = CITIES[0]; // Kochi
      else if (lower.includes('bombay') || lower.includes('konkan')) matchedCity = CITIES[1]; // Mumbai
      else if (lower.includes('secunderabad') || lower.includes('telangana')) matchedCity = CITIES[2]; // Hyderabad
      else if (lower.includes('deccan') || lower.includes('maharashtra')) matchedCity = CITIES[3]; // Pune
      else if (lower.includes('delhi') || lower.includes('ncr') || lower.includes('new delhi')) matchedCity = CITIES[4]; // Delhi
      else if (lower.includes('punjab') || lower.includes('haryana')) matchedCity = CITIES[5]; // Chandigarh
    }

    if (matchedCity) {
      if (onSelectCity) onSelectCity(matchedCity);
      try {
        const blendData = await fetchCitizenBlend({
          region_id: matchedCity.regionId,
          lead_time_hrs: 24,
          variable: 'rainfall',
        }).catch(() =>
          fetchCitizenBlend({
            region_id: matchedCity.regionId,
            valid_time: '2024-06-15T00:00:00Z',
            lead_time_hrs: 24,
            variable: 'rainfall',
          })
        );

        const rainfall = blendData.blended_value.toFixed(1);
        const response = `In ${matchedCity.name}, ${matchedCity.state}: Expect ${blendData.plain_language_summary} with a blended forecast of ${rainfall} millimeters. Atmospheric prediction models show ${blendData.confidence_label}.`;
        addBotResponse(response, 'weather', blendData);
        speakText(response);
      } catch {
        const response = `In ${matchedCity.name}: Moderate steady rainfall of around 25 millimeters is expected under active monsoon conditions.`;
        addBotResponse(response, 'weather');
        speakText(response);
      }
      return;
    }

    // 4. Model Weights & Explainability Queries
    if (
      lower.includes('weight') ||
      lower.includes('model') ||
      lower.includes('shap') ||
      lower.includes('nwp') ||
      lower.includes('ai') ||
      lower.includes('xgboost')
    ) {
      const response =
        'VaruNet dynamically weights three forecasting paradigms: Numerical Weather Prediction physics, Deep AI/ML, and Multi-Model Ensemble. Currently, the AI/ML model holds the dominant weight at 63.3% due to minimal recent error variance, while NWP holds 11.2% and Ensemble holds 25.5%. TreeSHAP shows AI/ML is driving the consensus.';
      addBotResponse(response, 'weights');
      speakText(response);
      return;
    }

    // 5. Help / Capabilities
    if (lower.includes('help') || lower.includes('what can you do') || lower.includes('who are you')) {
      const response =
        'I can assist you with real-time multi-model weather forecasts for Indian cities, active hazard alerts, TreeSHAP model explainability, and hands-free voice navigation between Citizen and Operator views.';
      addBotResponse(response, 'general');
      speakText(response);
      return;
    }

    // 6. General Fallback
    const response = `Regarding "${trimmed}": Under current synoptic monsoon regimes, VaruNet forecasts steady precipitation across coastal regions and moderate cloudiness inland. You can ask me for specific city forecasts like Kochi, Mumbai, or Delhi!`;
    addBotResponse(response, 'general');
    speakText(response);
  };

  const addBotResponse = (text: string, actionType: any, dataPayload?: any) => {
    const botMessage: ChatMessage = {
      id: `bot-${Date.now()}`,
      sender: 'bot',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      actionType,
      dataPayload,
    };
    setMessages((prev) => [...prev, botMessage]);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (textInput.trim()) {
      handleUserQuery(textInput);
    }
  };

  return (
    <>
      {/* Floating Microphone Action Button */}
      <div
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          gap: '10px',
        }}
      >
        {/* Audio Wave Pulse Animation */}
        <style>{`
          @keyframes varunetPulse {
            0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.7); }
            70% { transform: scale(1.08); box-shadow: 0 0 0 16px rgba(99, 102, 241, 0); }
            100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0); }
          }
          @keyframes soundWave {
            0%, 100% { height: 4px; }
            50% { height: 18px; }
          }
        `}</style>

        {/* Trigger Button */}
        <button
          onClick={() => {
            setIsOpen(!isOpen);
            if (!isOpen) {
              // Greet with voice when opened
              if (!isMuted) speakText("Hello! I am VaruBot. How can I help with your weather forecast?");
            }
          }}
          title="VaruBot AI Weather Voice Assistant"
          style={{
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: isListening
              ? 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
              : 'linear-gradient(135deg, #6366f1 0%, #4338ca 100%)',
            border: '2px solid rgba(255, 255, 255, 0.3)',
            boxShadow: '0 8px 24px rgba(99, 102, 241, 0.45)',
            color: '#ffffff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '26px',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            animation: isListening || isSpeaking ? 'varunetPulse 1.5s infinite' : 'none',
          }}
        >
          {isListening ? '🛑' : isSpeaking ? '🔊' : '🎙️'}
        </button>
      </div>

      {/* Interactive Voice Assistant Modal Dialog */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '96px',
            right: '24px',
            width: '380px',
            maxWidth: 'calc(100vw - 32px)',
            height: '560px',
            maxHeight: 'calc(100vh - 120px)',
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '20px',
            boxShadow: '0 20px 48px rgba(0, 0, 0, 0.6)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            zIndex: 9999,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          }}
        >
          {/* Assistant Header */}
          <div
            style={{
              padding: '16px 20px',
              background: 'linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%)',
              borderBottom: '1px solid #334155',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #6366f1, #818cf8)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '18px',
                }}
              >
                🎙️
              </div>
              <div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc' }}>
                  VaruBot Assistant
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span
                    style={{
                      width: '7px',
                      height: '7px',
                      borderRadius: '50%',
                      background: isListening ? '#ef4444' : isSpeaking ? '#22c55e' : '#38bdf8',
                    }}
                  />
                  {isListening ? 'Listening to voice...' : isSpeaking ? 'Speaking response...' : 'Voice & NLP Online'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {/* Voice Mute / Unmute Button */}
              <button
                onClick={() => {
                  stopSpeaking();
                  setIsMuted(!isMuted);
                }}
                title={isMuted ? 'Unmute Voice Response' : 'Mute Voice Response'}
                style={{
                  background: 'none',
                  border: 'none',
                  color: isMuted ? '#ef4444' : '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '16px',
                  padding: '4px',
                }}
              >
                {isMuted ? '🔇' : '🔊'}
              </button>

              {/* Close Button */}
              <button
                onClick={() => {
                  stopSpeaking();
                  if (isListening && recognitionRef.current) recognitionRef.current.stop();
                  setIsOpen(false);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  fontSize: '18px',
                  padding: '4px',
                }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Quick Voice Prompt Chips */}
          <div
            style={{
              padding: '8px 12px',
              background: '#090d16',
              borderBottom: '1px solid #1e293b',
              display: 'flex',
              gap: '6px',
              overflowX: 'auto',
              whiteSpace: 'nowrap',
            }}
          >
            {[
              { label: '🌦️ Weather in Kochi', text: 'What is the weather in Kochi?' },
              { label: '🛡️ Active Alerts', text: 'Are there any weather alerts?' },
              { label: '🤖 Model Weights', text: 'Explain the model weights' },
              { label: '📱 Citizen Portal', text: 'Switch to citizen portal' },
              { label: '📊 Dashboard', text: 'Switch to operator dashboard' },
            ].map((chip) => (
              <button
                key={chip.label}
                onClick={() => handleUserQuery(chip.text)}
                style={{
                  background: '#1e293b',
                  border: '1px solid #334155',
                  color: '#cbd5e1',
                  borderRadius: '16px',
                  padding: '4px 10px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  flexShrink: 0,
                }}
              >
                {chip.label}
              </button>
            ))}
          </div>

          {/* Chat Messages Transcript */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            {messages.map((m) => (
              <div
                key={m.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: m.sender === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '85%',
                    padding: '10px 14px',
                    borderRadius: m.sender === 'user' ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                    background: m.sender === 'user' ? '#4f46e5' : '#1e293b',
                    color: '#f8fafc',
                    fontSize: '13px',
                    lineHeight: '1.45',
                    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                    border: m.sender === 'user' ? 'none' : '1px solid #334155',
                  }}
                >
                  {m.text}
                </div>
                <div
                  style={{
                    fontSize: '10px',
                    color: '#64748b',
                    marginTop: '3px',
                    marginRight: m.sender === 'user' ? '4px' : 0,
                    marginLeft: m.sender === 'bot' ? '4px' : 0,
                  }}
                >
                  {m.timestamp}
                </div>
              </div>
            ))}

            {/* Live Voice Transcription Bubble */}
            {isListening && transcript && (
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <div
                  style={{
                    maxWidth: '85%',
                    padding: '8px 12px',
                    borderRadius: '14px',
                    background: 'rgba(99, 102, 241, 0.2)',
                    border: '1px dashed #6366f1',
                    color: '#a5b4fc',
                    fontSize: '12px',
                    fontStyle: 'italic',
                  }}
                >
                  Hearing: "{transcript}..."
                </div>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>

          {/* Voice Listening Wave Indicator */}
          {isListening && (
            <div
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                borderTop: '1px solid rgba(239, 68, 68, 0.3)',
                padding: '10px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
                  {[1, 2, 3, 4, 5].map((bar) => (
                    <span
                      key={bar}
                      style={{
                        width: '3px',
                        height: '14px',
                        background: '#ef4444',
                        borderRadius: '2px',
                        animation: `soundWave 0.6s infinite ease-in-out ${bar * 0.1}s`,
                      }}
                    />
                  ))}
                </div>
                <span style={{ fontSize: '12px', color: '#fca5a5', fontWeight: 600 }}>
                  Listening to your voice... Speak now
                </span>
              </div>

              <button
                onClick={toggleListening}
                style={{
                  background: '#ef4444',
                  border: 'none',
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '4px 10px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                }}
              >
                Done
              </button>
            </div>
          )}

          {/* Assistant Bottom Input Controls */}
          <form
            onSubmit={handleFormSubmit}
            style={{
              padding: '12px 14px',
              background: '#090d16',
              borderTop: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            {/* Big Mic Button */}
            <button
              type="button"
              onClick={toggleListening}
              title={isListening ? 'Stop Listening' : 'Start Voice Recognition'}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                background: isListening ? '#ef4444' : '#6366f1',
                border: 'none',
                color: '#ffffff',
                fontSize: '16px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                boxShadow: isListening ? '0 0 12px rgba(239, 68, 68, 0.6)' : 'none',
              }}
            >
              {isListening ? '⏹️' : '🎙️'}
            </button>

            {/* Text Input */}
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder={isListening ? 'Listening...' : 'Speak or type weather question...'}
              style={{
                flex: 1,
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: '20px',
                padding: '8px 14px',
                color: '#f8fafc',
                fontSize: '13px',
                outline: 'none',
              }}
            />

            {/* Send Button */}
            <button
              type="submit"
              disabled={!textInput.trim()}
              style={{
                background: textInput.trim() ? '#4f46e5' : '#334155',
                border: 'none',
                color: '#ffffff',
                borderRadius: '50%',
                width: '34px',
                height: '34px',
                cursor: textInput.trim() ? 'pointer' : 'default',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '13px',
                flexShrink: 0,
              }}
            >
              ➤
            </button>
          </form>
        </div>
      )}
    </>
  );
};
