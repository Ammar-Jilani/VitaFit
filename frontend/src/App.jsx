import React from 'react';
import { Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import About from './pages/About';
import Navbar from './components/Navbar';
import CalorieEstimation from './pages/CalorieEstimation';
import FitnessPlanner from './pages/FitnessPlanner';
function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/about" element={<About />} />
        <Route path="/calorie-estimation" element={<CalorieEstimation />} />
        <Route path="/fitness-planner" element={<FitnessPlanner />} />
      </Routes>
    </>
  );
}

export default App;
