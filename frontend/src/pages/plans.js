// src/pages/Plans.js
import React, { useState, useEffect } from "react";
import axios from "axios";
import "./plans.css";

function Plans() {
  const [plans, setPlans] = useState([]);

  useEffect(() => {
    // Replace with your API endpoint
    axios.get("/api/user/plans")
      .then((res) => {
        setPlans(res.data);
      })
      .catch((err) => {
        console.error("Error fetching plans:", err);
      });
  }, []);

  return (
    <div className="plans-page">
      <h1>My Plans</h1>
      {plans.length > 0 ? (
        plans.map((plan) => (
          <div key={plan.id} className="plan-card">
            <h2>{plan.title}</h2>
            <p>{plan.description}</p>
          </div>
        ))
      ) : (
        <p>You have no plans saved yet.</p>
      )}
    </div>
  );
}

export default Plans;
