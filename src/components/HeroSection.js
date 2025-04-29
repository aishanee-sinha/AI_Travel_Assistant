// src/components/HeroSection.js
import React from 'react';
import './HeroSection.css';

export default function HeroSection({ onSearch }) {
  const [q, setQ] = React.useState('');
  const submit = e => {
    e.preventDefault();
    onSearch(q);
  };

  return (
    <section className="hero">
      <div className="overlay"></div>
      <div className="hero-content fade-in">
        <h1>Hey, I’m Travelit — your travel agent who never sleeps.</h1>
        <p>Tell me where you want to go and I’ll handle flights, hotels, itineraries… in seconds.</p>
        <form onSubmit={submit} className="hero-search">
          <input
            type="text"
            className="hero-input"
            placeholder="Where to next?"
            value={q}
            onChange={e => setQ(e.target.value)}
            required
          />
          <button type="submit" className="hero-button">
            <i className="fas fa-search"></i>
          </button>
        </form>
      </div>
    </section>
  );
}
