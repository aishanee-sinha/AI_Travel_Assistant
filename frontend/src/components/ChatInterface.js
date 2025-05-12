import React, { useState, useRef, useEffect } from 'react';
import './ChatInterface.css';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [lastItinerary, setLastItinerary] = useState('');
  const [destination, setDestination] = useState('');
  const [duration, setDuration] = useState('');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const formatTime = (date) => date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const processResponse = (response) => {
    const sections = { itinerary: '', flights: [], hotels: [] };
    if (!response) return sections;
    const lines = response.split('\n');
    let currentSection = 'itinerary';
    for (let line of lines) {
      if (line.toLowerCase().includes('flight options')) { currentSection = 'flights'; continue; }
      else if (line.toLowerCase().includes('hotel options')) { currentSection = 'hotels'; continue; }
      if (currentSection === 'itinerary') {
        if (!line.toLowerCase().includes('flight options') && !line.toLowerCase().includes('hotel options')) {
          sections.itinerary += line + '\n';
        }
      }
    }
    sections.itinerary = sections.itinerary.trim();
    return sections;
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    const userMessage = { text: input, sender: 'user', timestamp: new Date(), status: 'sent' };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      });
      const data = await response.json();
      const sections = processResponse(data.response);
      const botMessage = { text: sections, sender: 'bot', timestamp: new Date(), status: 'read' };
      setMessages(prev => [...prev, botMessage]);
      if (sections.itinerary) setLastItinerary(sections.itinerary);
      // Try to extract destination and duration from the user input (simple guess)
      if (!destination) {
        const destMatch = input.match(/to ([A-Za-z ]+)/i);
        if (destMatch) setDestination(destMatch[1].trim());
      }
      if (!duration) {
        const durMatch = input.match(/(\d+)\s*days?/i);
        if (durMatch) setDuration(durMatch[1]);
      }
    } catch (error) {
      setMessages(prev => [...prev, { text: 'Sorry, I encountered an error. Please try again.', sender: 'bot', timestamp: new Date() }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Function to download the itinerary
  const downloadItinerary = async () => {
    if (!lastItinerary) {
      alert('No itinerary available to download!');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/api/download_pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          itinerary: lastItinerary,
          destination: destination || 'Your Trip',
          duration: duration || 'N/A'
        })
      });

      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `itinerary_${destination || 'trip'}_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (error) {
      console.error('PDF Download Error:', error);
      alert('Failed to download PDF: ' + error.message);
    }
  };

  const renderMessage = (message) => {
    const timeString = formatTime(message.timestamp);
    const sections = typeof message.text === 'object' ? message.text : { itinerary: message.text || '', flights: [], hotels: [] };

    return (
      <div className={`message ${message.sender}`}>
        <div className="message-content">
          {typeof message.text === 'object' && message.text.itinerary ? (
            <div className="itinerary-section">
              <h3>Your Itinerary</h3>
              <div className="itinerary-content">
                {message.text.itinerary.split('\n').map((line, index) => (
                  <p key={index}>{line}</p>
                ))}
              </div>
              <button
                className="big-download-button"
                onClick={downloadItinerary}
              >
                📥 DOWNLOAD ITINERARY PDF
              </button>
            </div>
          ) : (
            <div>
              {typeof message.text === 'string' && message.text.split('\n').map((line, index) => (
                <p key={index}>{line}</p>
              ))}
            </div>
          )}

          <div className="message-meta">
            <span className="time">{timeString}</span>
            {message.status === 'sent' && <span className="status">✓</span>}
            {message.status === 'read' && <span className="status read">✓✓</span>}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className="message-container">
            {renderMessage(message)}
          </div>
        ))}
        {isLoading && (
          <div className="message bot">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <form onSubmit={handleSendMessage} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about travel plans..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatInterface; 