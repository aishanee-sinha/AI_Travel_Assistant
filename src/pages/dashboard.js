import React from 'react';
import HeroSection   from '../components/HeroSection';
import FeaturedTrips from '../components/FeaturedTrips';

export default function Dashboard() {
  const handleSearch = q => {
    console.log('Searching for:', q);
    // your teammate will hook into this
  };

  return (
    <main>
      <HeroSection onSearch={handleSearch} />
      <FeaturedTrips />
    </main>
  );
}
