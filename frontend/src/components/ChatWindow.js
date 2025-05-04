import React, { useState, useRef, useEffect } from 'react';
import './ChatWindow.css';

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

    // Add user message to chat with typing animation
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

      // Process the response to extract different sections
      const sections = processResponse(data.response);

      // Add assistant's response to chat with typing animation
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
    // Split response into sections based on markers
    const sections = response.split('\n\n');
    return sections.map(section => {
      if (section.startsWith('✈️')) {
        return { type: 'flight', content: section };
      } else if (section.startsWith('🏨')) {
        return { type: 'hotel', content: section };
      } else if (section.startsWith('🌤️')) {
        return { type: 'weather', content: section };
      } else if (section.startsWith('📅')) {
        return { type: 'itinerary', content: section };
      } else {
        return { type: 'text', content: section };
      }
    });
  };

  const renderMessage = (message) => {
    if (message.sender === 'user') {
      return (
        <div className="message user-message">
          <div className="message-content">
            <div className="message-text">{message.text}</div>
            <div className="message-time">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
          </div>
        </div>
      );
    }

    return (
      <div className={`message assistant-message ${message.error ? 'error' : ''}`}>
        <div className="message-content">
          {Array.isArray(message.text) ? (
            message.text.map((section, index) => (
              <div key={index} className={`message-section ${section.type}`}>
                {section.content}
              </div>
            ))
          ) : (
            <div className="message-text">{message.text}</div>
          )}
          <div className="message-time">{new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>Travel Assistant</h2>
        <p>Ask me anything about travel planning!</p>
      </div>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={index} className="message-wrapper">
            {renderMessage(message)}
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
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask me anything about travel..."
          className="chat-input"
        />
        <button
          type="submit"
          className="send-button"
          disabled={isLoading || !input.trim()}
        >
          <span className="send-icon">→</span>
        </button>
      </form>
    </div>
  );
};

export default ChatWindow; 