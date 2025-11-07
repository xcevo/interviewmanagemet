import React, { useState } from 'react';
import './Dashboard.css';
import Categories from './Categories';
import Criteria from './Criteria';
import Questions from './Questions';
import Users from './Users';
import Validity from './Validity';

function Dashboard() {
  const [view, setView] = useState('categories');
  

  const renderContent = () => {
    switch (view) {
      case 'categories':
        return <Categories onSelect={(cat) => console.log('Selected:', cat)} />;
      case 'criteria':
        return <Criteria />;
      case 'questions':
        return <Questions />
      case 'users':
        return <Users />;
      

      default:
        return <p>Select a section</p>;
    }
  };

  return (
    <div className="dashboard-container">
      <aside className="sidebar">
        <h2>Admin Panel</h2>
        <button
          className={view === 'categories' ? 'active' : ''}
          onClick={() => setView('categories')}
        >
          Categories
        </button>
        <button
          className={view === 'criteria' ? 'active' : ''}
          onClick={() => setView('criteria')}
        >
          Criteria
        </button>
        <button
          className={view === 'questions' ? 'active' : ''}
          onClick={() => setView('questions')}
        >
          Questions
        </button>
        <button
          className={view === 'users' ? 'active' : ''}
          onClick={() => setView('users')}
        >
          Users
        </button>
        

        <button className="logout" onClick={() => window.location.reload()}>
          Logout
        </button>
      </aside>

      <main className="content">
        {renderContent()}
      </main>
    </div>
  );
}

export default Dashboard;
