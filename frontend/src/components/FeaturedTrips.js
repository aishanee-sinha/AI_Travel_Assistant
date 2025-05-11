import React from 'react';
import './FeaturedTrips.css';

const trips = [
  { title: 'South of France', icon: 'fas fa-car' },
  { title: 'Greece Getaway', icon: 'fas fa-umbrella-beach' },
  { title: 'Tokyo Adventure', icon: 'fas fa-city' },
];

export default function FeaturedTrips() {
  return (
    <section className="trips-grid">
      {trips.map(t => (
        <div key={t.title} className="trip-card fade-in">
          <i className={t.icon}></i>
          <h3>{t.title}</h3>
        </div>
      ))}
    </section>
  );
}
