import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Auth.css';

const Login = () => {
    const [formData, setFormData] = useState({
        email: '',
        password: ''
    });
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const response = await fetch('http://localhost:8000/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData),
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('token', data.token);
                localStorage.setItem('userName', data.name);
                navigate('/chat');
            } else {
                setError(data.message || 'Login failed');
            }
        } catch (err) {
            setError('An error occurred. Please try again.');
        }
    };

    return (
        <div className="auth-container">
            {/* Floating shapes for crazy UI */}
            <div className="auth-floating-shape shape1"></div>
            <div className="auth-floating-shape shape2"></div>
            <div className="auth-floating-shape shape3"></div>
            <div className="auth-box">
                <button
                    type="button"
                    className="back-button"
                    onClick={() => navigate('/')}
                    style={{
                        background: 'none',
                        border: 'none',
                        color: '#4f4fc4',
                        fontWeight: 700,
                        fontSize: '1.1rem',
                        marginBottom: '1rem',
                        cursor: 'pointer',
                        textAlign: 'left',
                        display: 'block',
                    }}
                >
                    ← Back
                </button>
                <h2>Welcome Back</h2>
                <p className="auth-subtitle">Sign in to continue your journey</p>

                {error && <div className="error-message">{error}</div>}

                <form onSubmit={handleSubmit} className="auth-form">
                    <div className="form-group">
                        <label htmlFor="email">Email</label>
                        <input
                            type="email"
                            id="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="Enter your email"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="Enter your password"
                            required
                        />
                    </div>

                    <button type="submit" className="auth-button">
                        Sign In
                    </button>
                </form>

                <p className="auth-switch">
                    Don't have an account?{' '}
                    <Link to="/signup" className="auth-link">
                        Sign Up
                    </Link>
                </p>
            </div>
        </div>
    );
};

export default Login; 