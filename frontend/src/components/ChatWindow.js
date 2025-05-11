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
        text: "Sorry, I encountered an error. Please try again.",
        sender: 'assistant',
        error: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const processResponse = (response) => {
    // Split by double newlines for sections
    return response.split('\n\n').map(section => ({ content: section }));
  };

  // Render all assistant sections as single cards with HTML content
  const renderStackedCards = (sections) => {
    if (!sections.length) return null;
    return (
      <div className="stacked-cards-container">
        {sections.map((section, idx) => (
          <div key={idx} className="section-card fade-in-stacked">
            <div
              className="section-card-content"
              dangerouslySetInnerHTML={{ __html: section.content }}
            />
          </div>
        ))}
      </div>
    );
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

    // Assistant message: clean stacked cards with HTML content
    return (
      <div className={`message assistant-message chat-bubble slide-in-left ${message.error ? 'error' : ''}`}>
        <div className="message-content">
          {Array.isArray(message.text)
            ? renderStackedCards(message.text)
            : <div className="message-text">{message.text}</div>}
          <div className="message-time">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="chat-container chat-gradient-bg">
      <div className="chat-header">
        <h2>Travel Assistant</h2>
        <p>Ask me anything about travel planning!</p>
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
          placeholder="Type your message..."
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