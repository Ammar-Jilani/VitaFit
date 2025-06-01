import React from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

function LandingPage() {
  const navigate = useNavigate();

  const handleCalorieClick = () => {
    navigate('/calorie-estimation');
  };

  const handlePlannerClick = () => {
    navigate('/fitness-planner');
  };

  return (
    <section className="landing">
      <div className="hero-image">
        <div className="overlay">
          <div className="hero-content">
            <h1>Welcome to <span>VitaFit</span></h1>
            <p>Your smart AI-powered fitness companion</p>
            <div className="hero-buttons">
              <button className="animated-btn" onClick={handleCalorieClick}>
                Calorie Estimation via Image
              </button>
              <button className="animated-btn alt" onClick={handlePlannerClick}>
                Fitness Planner & Report Generation
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default LandingPage;
