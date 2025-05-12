import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './navbar.css';

export default function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <nav className="navbar fade-in">
      <div className="logo">
        <i className="fas fa-plane"></i> Travelit.Ai
      </div>
      <button className="hamburger hide-sm" onClick={() => setOpen(o => !o)}>
        <i className={open ? 'fas fa-times' : 'fas fa-bars'}></i>
      </button>
      <ul className={`nav-links ${open ? 'open' : ''}`}>
        <li><Link to="/" onClick={() => setOpen(false)}>Home</Link></li>
        <li><Link to="/login" onClick={() => setOpen(false)}>Login</Link></li>
        <li><Link to="/about" onClick={() => setOpen(false)}>About Us</Link></li>
        <li><Link to="/plans" onClick={() => setOpen(false)}>My Plans</Link></li>
      </ul>
    </nav>
);
}
