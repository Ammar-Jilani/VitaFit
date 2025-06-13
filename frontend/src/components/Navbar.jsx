import React from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

function Navbar() {
  return (
    <nav className="navbar">
      <Link to="/" className="logo-link"> {/* Added Link here */}
        <div className="logo">VitaFit</div>
      </Link>
      <ul className="nav-links">
        {/* Removed <li><Link to="/">Home</Link></li> */}
        <li><Link to="/about">About</Link></li>
      </ul>
    </nav>
  );
}

export default Navbar;