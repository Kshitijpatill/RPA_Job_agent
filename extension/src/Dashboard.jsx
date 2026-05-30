import { useState, useEffect } from 'react';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState('vault');
  const [appMode, setAppMode] = useState('semi'); 
  const [agentPortal, setAgentPortal] = useState('linkedin');
  const [agentState, setAgentState] = useState('idle');
  
  // Explicitly configured state structure to resolve structural field confusion
  const [profileData, setProfileData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    gender: '',
    dob: '',
    location: '',
    expected_salary: '',
    skills: ''
  });
  const [jobs, setJobs] = useState([]);
  const [status, setStatus] = useState('');

  useEffect(() => {
    chrome.storage.local.get(['appMode'], (res) => {
      if (res.appMode) setAppMode(res.appMode);
    });
    fetchProfile();
    fetchJobs();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/profile/");
      const data = await res.json();
      setProfileData(prev => ({ ...prev, ...data }));
    } catch (e) {
      console.log("Backend connection error");
    }
  };

  const fetchJobs = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/jobs/");
      const data = await res.json();
      setJobs(data);
    } catch (e) {
      console.log("Backend offline");
    }
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setStatus("Saving properties...");
    try {
      await fetch("http://127.0.0.1:8000/profile/update/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: profileData })
      });
      setStatus("✅ Identity Profile Vault Synchronized!");
      setTimeout(() => setStatus(""), 3000);
    } catch (error) {
      setStatus("❌ Encryption transmission failure.");
    }
  };

  const handleModeChange = (mode) => {
    setAppMode(mode);
    chrome.storage.local.set({ appMode: mode });
  };

  const handlePrepareAgent = async () => {
    setAgentState('waiting_login');
    try {
      await fetch("http://127.0.0.1:8000/agent/prepare/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ portal: agentPortal })
      });
    } catch (e) {
      console.error("Backend offline");
    }
  };

  const handleRunAgent = async () => {
    setAgentState('running');
    try {
      await fetch("http://127.0.0.1:8000/agent/start/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ portal: agentPortal })
      });
    } catch (e) {
      setAgentState('idle');
    }
  };

  return (
    <div style={{ maxWidth: '900px', margin: '40px auto', padding: '25px', fontFamily: 'system-ui, sans-serif', backgroundColor: '#fff', borderRadius: '12px', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}>
      <h1 style={{ textAlign: 'center', color: '#1e293b', marginBottom: '30px' }}>AI Job Agent Command Center</h1>
      
      {/* MODE CONFIGURATION LAYER */}
      <div style={{ display: 'flex', backgroundColor: '#f1f5f9', borderRadius: '10px', padding: '6px', marginBottom: '25px' }}>
        <button onClick={() => handleModeChange('semi')} style={{ flex: 1, padding: '12px', fontWeight: '600', borderRadius: '8px', border: 'none', cursor: 'pointer', backgroundColor: appMode === 'semi' ? '#0284c7' : 'transparent', color: appMode === 'semi' ? 'white' : '#64748b', transition: 'all 0.2s' }}>
          ⚡ Semi-Manual Integration
        </button>
        <button onClick={() => handleModeChange('agent')} style={{ flex: 1, padding: '12px', fontWeight: '600', borderRadius: '8px', border: 'none', cursor: 'pointer', backgroundColor: appMode === 'agent' ? '#ef4444' : 'transparent', color: appMode === 'agent' ? 'white' : '#64748b', transition: 'all 0.2s' }}>
          🤖 Full Robotic Agent
        </button>
      </div>

      {appMode === 'semi' ? (
        <div style={{ backgroundColor: '#f0f9ff', color: '#0369a1', padding: '15px', borderRadius: '8px', marginBottom: '30px', fontSize: '14px' }}>
          <b>Status Active:</b> Running structural listener inside extension background context. Navigate to any target application window and activate the toolbar icon to trigger field populations.
        </div>
      ) : (
        <div style={{ backgroundColor: '#fef2f2', color: '#991b1b', padding: '20px', borderRadius: '8px', marginBottom: '30px' }}>
          <h4 style={{ margin: '0 0 10px 0' }}>Robotic Process Loop Setup</h4>
          
          {agentState === 'idle' && (
            <div>
              <select value={agentPortal} onChange={(e) => setAgentPortal(e.target.value)} style={{ padding: '8px', borderRadius: '6px', border: '1px solid #fca5a5', marginRight: '10px' }}>
                <option value="linkedin">LinkedIn Jobs</option>
                <option value="indeed">Indeed Portal</option>
              </select>
              <button onClick={handlePrepareAgent} style={{ padding: '8px 16px', backgroundColor: '#ef4444', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                Deploy Automated Frame
              </button>
            </div>
          )}

          {agentState === 'waiting_login' && (
            <div style={{ backgroundColor: 'white', padding: '15px', borderRadius: '8px', border: '1px solid #fca5a5', marginTop: '10px' }}>
              <p style={{ margin: '0 0 10px 0', fontSize: '14px' }}>A new debugging tab has opened. Please go to that tab and <b>log in manually</b> if required.</p>
              <button onClick={handleRunAgent} style={{ padding: '8px 16px', backgroundColor: '#059669', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '600' }}>
                ✅ I am logged in. Run Agent!
              </button>
            </div>
          )}

          {agentState === 'running' && (
            <div>
              <p style={{ fontWeight: '600', color: '#059669' }}>🏃 Agent is currently running autonomously.</p>
              <button onClick={() => setAgentState('idle')} style={{ padding: '8px 16px', backgroundColor: '#94a3b8', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                Stop / Reset Agent
              </button>
            </div>
          )}
        </div>
      )}

      {/* VIEWS SELECTION NAV */}
      <div style={{ display: 'flex', borderBottom: '2px solid #e2e8f0', marginBottom: '25px' }}>
        <button onClick={() => setActiveTab('vault')} style={{ padding: '12px 24px', fontSize: '15px', fontWeight: '600', cursor: 'pointer', border: 'none', background: 'none', color: activeTab === 'vault' ? '#0284c7' : '#64748b', borderBottom: activeTab === 'vault' ? '2px solid #0284c7' : 'none' }}>
          👤 User Profile Vault
        </button>
        <button onClick={() => setActiveTab('tracker')} style={{ padding: '12px 24px', fontSize: '15px', fontWeight: '600', cursor: 'pointer', border: 'none', background: 'none', color: activeTab === 'tracker' ? '#0284c7' : '#64748b', borderBottom: activeTab === 'tracker' ? '2px solid #0284c7' : 'none' }}>
          📊 Metrics Ledger
        </button>
      </div>

      {/* CORE IDENTITY PROFILE TAB */}
      {activeTab === 'vault' && (
        <form onSubmit={handleSaveProfile} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {Object.keys(profileData).map(key => (
            <div key={key} style={{ display: 'flex', flexDirection: 'column', gridColumn: key === 'skills' ? 'span 2' : 'auto' }}>
              <label style={{ fontSize: '14px', fontWeight: '600', color: '#334155', marginBottom: '6px', textTransform: 'capitalize' }}>
                {key.replace('_', ' ')}
              </label>
              {key === 'skills' ? (
                <textarea 
                  rows={4}
                  value={profileData[key] || ''} 
                  onChange={(e) => setProfileData({...profileData, [key]: e.target.value})}
                  style={{ padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px', resize: 'vertical', fontFamily: 'inherit' }}
                />
              ) : (
                <input 
                  type={key === 'dob' ? 'date' : 'text'} 
                  value={profileData[key] || ''} 
                  onChange={(e) => setProfileData({...profileData, [key]: e.target.value})}
                  style={{ padding: '10px', border: '1px solid #cbd5e1', borderRadius: '6px' }}
                />
              )}
            </div>
          ))}
          <div style={{ gridColumn: 'span 2', textAlign: 'right', marginTop: '10px' }}>
            <button type="submit" style={{ padding: '12px 24px', backgroundColor: '#0f172a', color: 'white', border: 'none', borderRadius: '6px', fontWeight: '600', cursor: 'pointer' }}>
              Commit Modifications
            </button>
            {status && <p style={{ margin: '10px 0 0 0', fontSize: '14px', fontWeight: '500', color: '#059669' }}>{status}</p>}
          </div>
        </form>
      )}

      {/* TRACKER TAB */}
      {activeTab === 'tracker' && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ color: '#334155', margin: 0 }}>Submissions Executed Ledger ({jobs.length})</h3>
            <button onClick={fetchJobs} style={{ padding: '8px 15px', cursor: 'pointer', borderRadius: '5px', border: '1px solid #cbd5e1', backgroundColor: '#fff' }}>Refresh</button>
          </div>
          
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '14px' }}>
            <thead>
              <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #e2e8f0' }}>
                <th style={{ padding: '12px' }}>Date</th>
                <th style={{ padding: '12px' }}>Company</th>
                <th style={{ padding: '12px' }}>Role</th>
                <th style={{ padding: '12px' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                  <td style={{ padding: '12px' }}>{new Date(job.applied_on).toLocaleDateString()}</td>
                  <td style={{ padding: '12px', fontWeight: '600', color: '#1e293b' }}>{job.company}</td>
                  <td style={{ padding: '12px', color: '#64748b' }}>{job.role}</td>
                  <td style={{ padding: '12px' }}>
                    <span style={{ backgroundColor: '#dcfce7', color: '#166534', padding: '4px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: '600' }}>
                      {job.status}
                    </span>
                  </td>
                </tr>
              ))}
              {jobs.length === 0 && (
                <tr>
                  <td colSpan="4" style={{ padding: '20px', textAlign: 'center', color: '#94a3b8' }}>No submissions recorded yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}