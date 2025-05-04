import React, { useState } from 'react';
import HeroSection from '../components/HeroSection';
import FeaturedTrips from '../components/FeaturedTrips';
import axios from 'axios';
import './dashboard.css';

export default function Dashboard() {
  const [chatResponse, setChatResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSearch = async (query) => {
    try {
      setIsLoading(true);
      const response = await axios.post('http://localhost:8000/api/chat', {
        message: query
      });
      setChatResponse(response.data.response);
    } catch (error) {
      console.error('Error:', error);
      setChatResponse('Sorry, there was an error processing your request.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main>
      <HeroSection onSearch={handleSearch} />
      {isLoading && <div className="loading">Processing your request...</div>}
      {chatResponse && (
        <div className="chat-response">
          <h3>Travel Assistant Response:</h3>
          <div dangerouslySetInnerHTML={{ __html: chatResponse.replace(/\n/g, '<br />') }} />
        </div>
      )}
      <FeaturedTrips />
    </main>
  );
}
