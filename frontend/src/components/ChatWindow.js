import React, { useState, useRef, useEffect } from 'react';
import './ChatWindow.css';
import FlightCard from './FlightCard';
import HotelCard from './HotelCard';

const SECTION_ICONS = {
  itinerary: '🗓️',
  flight: '✈️',
  hotel: '🏨',
  weather: '🌤️',
  text: 'ℹ️',
};

const SECTION_LABELS = {
  itinerary: 'Itinerary',
  flight: 'Flights',
  hotel: 'Hotels',
  weather: 'Weather',
  text: 'Info',
};

const ChatWindow = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const processResponse = (response) => {
    // Split response into sections based on headers
    const sections = [];
    const lines = response.split('\n');
    let currentSection = { type: 'text', content: [] };

    lines.forEach(line => {
      if (line.startsWith('Flights:')) {
        if (currentSection.content.length > 0) {
          sections.push(currentSection);
        }
        currentSection = { type: 'flight', content: [] };
      } else if (line.startsWith('Hotels:')) {
        if (currentSection.content.length > 0) {
          sections.push(currentSection);
        }
        currentSection = { type: 'hotel', content: [] };
      } else if (line.trim()) {
        currentSection.content.push(line);
      }
    });

    if (currentSection.content.length > 0) {
      sections.push(currentSection);
    }

    return sections;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);

    setMessages(prev => [...prev, { text: userMessage, sender: 'user' }]);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      const sections = processResponse(data.response);
      setMessages(prev => [...prev, { text: sections, sender: 'assistant' }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        text: [{ type: 'text', content: ["Sorry, I encountered an error. Please try again."] }],
        sender: 'assistant',
        error: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const renderSection = (section) => {
    switch (section.type) {
      case 'flight':
        return (
          <div className="section flight-section">
            <h3>✈️ Flight Options</h3>
            {section.content.map((line, idx) => (
              <div key={idx} className="flight-option">
                {line}
              </div>
            ))}
          </div>
        );
      case 'hotel':
        return (
          <div className="section hotel-section">
            <h3>🏨 Hotel Options</h3>
            {section.content.map((line, idx) => (
              <div key={idx} className="hotel-option">
                {line}
              </div>
            ))}
          </div>
        );
      default:
        return (
          <div className="section text-section">
            {section.content.map((line, idx) => (
              <p key={idx}>{line}</p>
            ))}
          </div>
        );
    }
  };

  const renderMessage = (message, msgIdx) => {
    if (message.sender === 'user') {
      return (
        <div className="message user-message chat-bubble slide-in-right">
          <div className="message-content">
            <div className="message-text">{message.text}</div>
            <div className="message-time">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
          </div>
        </div>
      );
    }

    return (
      <div className={`message assistant-message chat-bubble slide-in-left ${message.error ? 'error' : ''}`}>
        <div className="message-content">
          {Array.isArray(message.text) ? (
            <div className="sections-container">
              {message.text.map((section, idx) => (
                <div key={idx} className="section-wrapper">
                  {renderSection(section)}
                </div>
              ))}
            </div>
          ) : (
            <div className="message-text">{message.text}</div>
          )}
          <div className="message-time">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="chat-container chat-gradient-bg">
      <div className="chat-header">
        <h2>Travel Assistant</h2>
        <p>Let's plan your perfect trip together!</p>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className="message-wrapper">
            {renderMessage(message, index)}
          </div>
        ))}
        {isLoading && (
          <div className="message assistant-message">
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

      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tell me about your travel plans..."
          ref={inputRef}
        />
        <button type="submit" disabled={isLoading}>
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatWindow;