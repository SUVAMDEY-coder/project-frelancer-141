from http.server import HTTPServer, BaseHTTPRequestHandler
import json, uuid, datetime, hashlib, os, urllib.parse

# ─────────────────────────────────────────────
# IN-MEMORY DATABASE
# ─────────────────────────────────────────────
DB = {
    "users": {},
    "projects": {},
    "transactions": []
}

SESSIONS = {}  # session_id -> user_id

def now():
    return datetime.datetime.now().isoformat()

def gen_id():
    return str(uuid.uuid4())[:8].upper()

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

def log_activity(text, project_id=None, user_id=None):
    DB["transactions"].append({
        "id": gen_id(), "time": now(),
        "text": text, "project_id": project_id, "user_id": user_id
    })

# ─────────────────────────────────────────────
# HTML
# ─────────────────────────────────────────────
HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LockWork — Freelance Escrow Platform</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --navy: #0a0e1a; --navy2: #111827; --navy3: #1a2235;
    --amber: #f59e0b; --amber2: #fbbf24; --amber-dim: #92600a;
    --green: #10b981; --red: #ef4444; --blue: #3b82f6;
    --text: #e2e8f0; --muted: #64748b; --border: #1e2d45;
    --mono: 'Space Mono', monospace; --sans: 'Syne', sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--navy); color: var(--text); font-family: var(--mono); min-height: 100vh; overflow-x: hidden; }
  body::before {
    content: ''; position: fixed; inset: 0;
    background-image: linear-gradient(rgba(245,158,11,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(245,158,11,0.03) 1px, transparent 1px);
    background-size: 40px 40px; pointer-events: none; z-index: 0;
  }
  .container { max-width: 1100px; margin: 0 auto; padding: 0 24px; position: relative; z-index: 1; }
  nav { border-bottom: 1px solid var(--border); padding: 16px 0; position: sticky; top: 0; background: rgba(10,14,26,0.95); backdrop-filter: blur(8px); z-index: 100; }
  nav .inner { display: flex; align-items: center; justify-content: space-between; max-width: 1100px; margin: 0 auto; padding: 0 24px; }
  .logo { font-family: var(--sans); font-weight: 800; font-size: 1.4rem; color: var(--amber); letter-spacing: -0.5px; }
  .logo span { color: var(--text); }
  nav a { color: var(--muted); text-decoration: none; font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase; transition: color 0.2s; }
  nav a:hover { color: var(--amber); }
  .nav-links { display: flex; gap: 24px; align-items: center; }
  .btn { display: inline-block; padding: 8px 18px; border-radius: 4px; font-family: var(--mono); font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; cursor: pointer; border: none; transition: all 0.2s; text-decoration: none; }
  .btn-amber { background: var(--amber); color: var(--navy); font-weight: 700; }
  .btn-amber:hover { background: var(--amber2); }
  .btn-outline { border: 1px solid var(--border); color: var(--text); background: transparent; }
  .btn-outline:hover { border-color: var(--amber); color: var(--amber); }
  .btn-sm { padding: 6px 12px; font-size: 0.7rem; }
  .btn-green { background: var(--green); color: white; }
  .btn-red { background: var(--red); color: white; }
  .hero { padding: 80px 0 60px; }
  .hero-stamp { display: inline-block; border: 2px solid var(--amber-dim); color: var(--amber); font-size: 0.65rem; letter-spacing: 0.2em; text-transform: uppercase; padding: 4px 12px; margin-bottom: 24px; }
  .hero h1 { font-family: var(--sans); font-size: clamp(2.2rem, 5vw, 4rem); font-weight: 800; line-height: 1.05; max-width: 700px; margin-bottom: 20px; }
  .hero h1 em { color: var(--amber); font-style: normal; }
  .hero p { color: var(--muted); font-size: 0.9rem; max-width: 480px; line-height: 1.7; margin-bottom: 36px; }
  .hero-actions { display: flex; gap: 12px; flex-wrap: wrap; }
  .stats-bar { display: grid; grid-template-columns: repeat(3, 1fr); border: 1px solid var(--border); margin: 40px 0; background: var(--navy2); }
  .stat { padding: 20px 24px; border-right: 1px solid var(--border); }
  .stat:last-child { border-right: none; }
  .stat-n { font-family: var(--sans); font-size: 2rem; font-weight: 800; color: var(--amber); }
  .stat-l { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px; }
  .section { padding: 48px 0; }
  .section-label { font-size: 0.65rem; letter-spacing: 0.2em; text-transform: uppercase; color: var(--amber); margin-bottom: 16px; }
  .steps { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 2px; background: var(--border); border: 1px solid var(--border); }
  .step { background: var(--navy2); padding: 28px 24px; }
  .step-num { font-size: 0.65rem; color: var(--amber); letter-spacing: 0.15em; margin-bottom: 12px; }
  .step h3 { font-family: var(--sans); font-weight: 600; font-size: 1rem; margin-bottom: 8px; }
  .step p { font-size: 0.78rem; color: var(--muted); line-height: 1.6; }
  .page { display: none; padding: 40px 0 80px; }
  .page.active { display: block; }
  .page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 32px; gap: 16px; flex-wrap: wrap; }
  .page-header h2 { font-family: var(--sans); font-size: 1.6rem; font-weight: 700; }
  .card { background: var(--navy2); border: 1px solid var(--border); padding: 24px; margin-bottom: 16px; }
  .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
  .card-title { font-family: var(--sans); font-size: 1rem; font-weight: 600; }
  .card-id { font-size: 0.65rem; color: var(--muted); letter-spacing: 0.1em; }
  .badge { display: inline-block; padding: 2px 8px; font-size: 0.65rem; letter-spacing: 0.1em; text-transform: uppercase; border-radius: 2px; }
  .badge-pending { background: rgba(245,158,11,0.15); color: var(--amber); }
  .badge-active { background: rgba(59,130,246,0.15); color: var(--blue); }
  .badge-review { background: rgba(168,85,247,0.15); color: #a855f7; }
  .badge-complete { background: rgba(16,185,129,0.15); color: var(--green); }
  .badge-locked { background: rgba(100,116,139,0.15); color: var(--muted); }
  .form-group { margin-bottom: 20px; }
  label { display: block; font-size: 0.7rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }
  input, textarea, select { width: 100%; background: var(--navy); border: 1px solid var(--border); color: var(--text); padding: 10px 14px; font-family: var(--mono); font-size: 0.85rem; border-radius: 2px; outline: none; transition: border-color 0.2s; }
  input:focus, textarea:focus { border-color: var(--amber); }
  textarea { resize: vertical; min-height: 80px; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .milestone-item { display: flex; align-items: center; gap: 12px; padding: 14px 18px; border: 1px solid var(--border); margin-bottom: 2px; background: var(--navy3); transition: border-color 0.2s; }
  .milestone-item:hover { border-color: var(--amber-dim); }
  .milestone-num { font-size: 0.65rem; color: var(--amber); min-width: 28px; }
  .milestone-title { flex: 1; font-size: 0.85rem; }
  .milestone-amount { font-family: var(--sans); font-weight: 600; color: var(--amber); font-size: 0.9rem; min-width: 80px; text-align: right; }
  .milestone-actions { display: flex; gap: 8px; }
  .escrow-box { border: 1px solid var(--amber-dim); background: rgba(245,158,11,0.04); padding: 20px 24px; margin-bottom: 20px; position: relative; }
  .escrow-box::before { content: '🔒 ESCROW'; position: absolute; top: -10px; left: 16px; background: var(--navy2); padding: 0 8px; font-size: 0.65rem; letter-spacing: 0.15em; color: var(--amber); }
  .escrow-amount { font-family: var(--sans); font-size: 2rem; font-weight: 800; color: var(--amber); }
  .escrow-meta { font-size: 0.75rem; color: var(--muted); margin-top: 6px; }
  .tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: 28px; }
  .tab { padding: 10px 20px; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; }
  .tab.active { color: var(--amber); border-bottom-color: var(--amber); }
  .contract-preview { background: var(--navy3); border: 1px solid var(--border); padding: 32px; font-size: 0.78rem; line-height: 1.8; font-family: var(--mono); white-space: pre-wrap; color: var(--text); max-height: 400px; overflow-y: auto; }
  .log-entry { display: flex; gap: 14px; padding: 12px 0; border-bottom: 1px solid var(--border); align-items: flex-start; }
  .log-time { font-size: 0.65rem; color: var(--muted); min-width: 80px; padding-top: 2px; }
  .log-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--amber); margin-top: 5px; flex-shrink: 0; }
  .log-text { font-size: 0.8rem; line-height: 1.5; }
  .auth-box { max-width: 460px; margin: 80px auto; }
  .auth-box .logo { font-size: 1.6rem; margin-bottom: 32px; display: block; }
  .auth-toggle { font-size: 0.75rem; color: var(--muted); margin-top: 20px; text-align: center; }
  .auth-toggle a { color: var(--amber); cursor: pointer; text-decoration: none; }
  .alert { padding: 12px 16px; font-size: 0.8rem; margin-bottom: 20px; border-left: 3px solid; }
  .alert-err { background: rgba(239,68,68,0.08); border-color: var(--red); color: #fca5a5; }
  .alert-ok { background: rgba(16,185,129,0.08); border-color: var(--green); color: #6ee7b7; }
  .progress-bar { height: 4px; background: var(--border); margin: 12px 0; }
  .progress-fill { height: 100%; background: var(--amber); transition: width 0.5s; }
  .flex { display: flex; } .items-center { align-items: center; } .justify-between { justify-content: space-between; }
  .mt-8 { margin-top: 8px; } .mt-16 { margin-top: 16px; }
  .text-muted { color: var(--muted); font-size: 0.78rem; } .text-amber { color: var(--amber); } .text-green { color: var(--green); }
  .bold { font-weight: 700; } .w-full { width: 100%; }
  .role-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 20px 0; }
  .role-card { padding: 20px; border: 2px solid var(--border); cursor: pointer; transition: all 0.2s; text-align: center; }
  .role-card:hover { border-color: var(--amber-dim); }
  .role-card.selected { border-color: var(--amber); background: rgba(245,158,11,0.06); }
  .role-card .role-icon { font-size: 1.8rem; margin-bottom: 8px; }
  .role-card .role-name { font-family: var(--sans); font-weight: 600; font-size: 0.9rem; }
  .role-card .role-desc { font-size: 0.7rem; color: var(--muted); margin-top: 4px; }
  .empty-state { text-align: center; padding: 60px 20px; color: var(--muted); font-size: 0.85rem; }
  .empty-state .icon { font-size: 2.5rem; margin-bottom: 12px; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
  .animate-in { animation: fadeIn 0.3s ease; }
  @media (max-width: 600px) { .form-row { grid-template-columns: 1fr; } .stats-bar { grid-template-columns: 1fr; } .role-cards { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<nav>
  <div class="inner">
    <div class="logo">Lock<span>Work</span></div>
    <div class="nav-links">
      <a href="#" onclick="showPage('home')">Home</a>
      <a href="#" onclick="showPage('how')">How It Works</a>
      <span id="authNav"></span>
    </div>
  </div>
</nav>

<div id="page-home" class="page active">
  <div class="container">
    <div class="hero">
      <div class="hero-stamp">Freelance Trust Infrastructure</div>
      <h1>Work gets done.<br><em>Everyone gets paid.</em></h1>
      <p>LockWork eliminates freelancer ghosting and payment disputes through milestone-based escrow, identity anchoring, and enforceable digital contracts.</p>
      <div class="hero-actions">
        <button class="btn btn-amber" onclick="showPage('auth')">Get Started Free</button>
        <button class="btn btn-outline" onclick="showPage('how')">See How It Works</button>
      </div>
    </div>
    <div class="stats-bar">
      <div class="stat"><div class="stat-n" id="statProjects">0</div><div class="stat-l">Active Projects</div></div>
      <div class="stat"><div class="stat-n" id="statEscrow">$0</div><div class="stat-l">Funds in Escrow</div></div>
      <div class="stat"><div class="stat-n" id="statCompleted">0</div><div class="stat-l">Milestones Completed</div></div>
    </div>
    <div class="section">
      <div class="section-label">The Problem</div>
      <h2 style="font-family:var(--sans);font-size:1.8rem;font-weight:700;margin-bottom:32px;">Informal hiring is broken</h2>
      <div class="steps">
        <div class="step"><div class="step-num">PROBLEM 01</div><h3>Freelancers ghost</h3><p>After receiving partial payment, workers disappear leaving projects incomplete with no recourse.</p></div>
        <div class="step"><div class="step-num">PROBLEM 02</div><h3>No legal framework</h3><p>Informal channels — WhatsApp, referrals, social — create agreements with zero enforceability.</p></div>
        <div class="step"><div class="step-num">PROBLEM 03</div><h3>Asymmetric trust</h3><p>Both sides take on risk with no mechanism to balance it.</p></div>
        <div class="step"><div class="step-num">PROBLEM 04</div><h3>Identity is anonymous</h3><p>Workers face zero reputational cost to abandon a project.</p></div>
      </div>
    </div>
  </div>
</div>

<div id="page-how" class="page">
  <div class="container">
    <div style="padding:48px 0 80px;">
      <div class="section-label">The Solution</div>
      <h2 style="font-family:var(--sans);font-size:1.8rem;font-weight:700;margin-bottom:32px;">How LockWork protects both sides</h2>
      <div class="steps" style="margin-bottom:40px;">
        <div class="step"><div class="step-num">STEP 01</div><h3>Business creates project</h3><p>Define deliverables, set milestone phases with individual amounts, and invite the freelancer by email.</p></div>
        <div class="step"><div class="step-num">STEP 02</div><h3>Funds locked in escrow</h3><p>Business deposits total budget. Money is committed but not released yet.</p></div>
        <div class="step"><div class="step-num">STEP 03</div><h3>Freelancer accepts & delivers</h3><p>Freelancer reviews contract, accepts the project, and submits each milestone upon completion.</p></div>
        <div class="step"><div class="step-num">STEP 04</div><h3>Business approves, funds release</h3><p>Each milestone approval triggers automatic escrow release. IP transfers only on full completion.</p></div>
      </div>
      <div style="text-align:center;margin-top:40px;"><button class="btn btn-amber" onclick="showPage('auth')">Start a Project Now</button></div>
    </div>
  </div>
</div>

<div id="page-auth" class="page">
  <div class="container">
    <div class="auth-box animate-in">
      <span class="logo">Lock<span style="color:var(--text)">Work</span></span>
      <div id="authAlert"></div>
      <div id="loginForm">
        <div class="section-label">Sign In</div>
        <div class="form-group"><label>Email</label><input type="email" id="loginEmail" placeholder="you@company.com"></div>
        <div class="form-group"><label>Password</label><input type="password" id="loginPass" placeholder="••••••••"></div>
        <button class="btn btn-amber w-full" onclick="login()">Sign In →</button>
        <div class="auth-toggle">No account? <a onclick="toggleAuth('register')">Create one</a></div>
        <div class="auth-toggle" style="margin-top:12px;">
          <a onclick="demoLogin('business')">⚡ Demo as Business</a> &nbsp;|&nbsp; <a onclick="demoLogin('freelancer')">⚡ Demo as Freelancer</a>
        </div>
      </div>
      <div id="registerForm" style="display:none;">
        <div class="section-label">Create Account</div>
        <div class="form-group"><label>Full Name</label><input type="text" id="regName" placeholder="Alex Johnson"></div>
        <div class="form-group"><label>Email</label><input type="email" id="regEmail" placeholder="you@company.com"></div>
        <div class="form-group"><label>Password</label><input type="password" id="regPass" placeholder="Choose a password"></div>
        <div class="form-group">
          <label>I am a...</label>
          <div class="role-cards">
            <div class="role-card selected" id="roleClient" onclick="selectRole('client')"><div class="role-icon">🏢</div><div class="role-name">Business / Client</div><div class="role-desc">I hire freelancers</div></div>
            <div class="role-card" id="roleFreelancer" onclick="selectRole('freelancer')"><div class="role-icon">👤</div><div class="role-name">Freelancer</div><div class="role-desc">I do the work</div></div>
          </div>
        </div>
        <button class="btn btn-amber w-full" onclick="register()">Create Account →</button>
        <div class="auth-toggle">Already have an account? <a onclick="toggleAuth('login')">Sign in</a></div>
      </div>
    </div>
  </div>
</div>

<div id="page-dashboard" class="page">
  <div class="container">
    <div class="page-header">
      <div><h2 id="dashTitle">Dashboard</h2><p id="dashSubtitle" class="text-muted"></p></div>
      <div id="dashActions"></div>
    </div>
    <div class="tabs">
      <div class="tab active" id="tab-projects" onclick="switchTab('projects')">Projects</div>
      <div class="tab" id="tab-activity" onclick="switchTab('activity')">Activity Log</div>
      <div class="tab" id="tab-profile" onclick="switchTab('profile')">My Profile</div>
    </div>
    <div id="tabContent"></div>
  </div>
</div>

<div id="page-newproject" class="page">
  <div class="container">
    <div style="padding:40px 0 80px;max-width:680px;">
      <div class="page-header">
        <div><h2>New Project</h2><p class="text-muted">Define scope, milestones, and lock funds in escrow</p></div>
        <button class="btn btn-outline btn-sm" onclick="showPage('dashboard')">← Back</button>
      </div>
      <div id="newProjectAlert"></div>
      <div class="card">
        <div class="section-label" style="margin-bottom:20px;">Project Details</div>
        <div class="form-group"><label>Project Title</label><input type="text" id="projTitle" placeholder="e.g. E-commerce Website Redesign"></div>
        <div class="form-group"><label>Description & Deliverables</label><textarea id="projDesc" placeholder="Describe what needs to be done..."></textarea></div>
        <div class="form-row">
          <div class="form-group"><label>Freelancer Email</label><input type="email" id="projFreelancer" placeholder="freelancer@email.com"></div>
          <div class="form-group"><label>Deadline</label><input type="date" id="projDeadline"></div>
        </div>
      </div>
      <div class="card">
        <div class="flex justify-between items-center" style="margin-bottom:20px;">
          <div class="section-label" style="margin-bottom:0;">Milestones & Escrow</div>
          <button class="btn btn-outline btn-sm" onclick="addMilestone()">+ Add Milestone</button>
        </div>
        <p class="text-muted" style="font-size:0.75rem;margin-bottom:16px;">Break the project into phases. Funds released only upon your approval.</p>
        <div id="milestoneInputs"></div>
        <div class="escrow-box" style="margin-top:20px;">
          <div class="flex justify-between items-center">
            <div><div class="escrow-amount" id="totalAmount">$0.00</div><div class="escrow-meta">Total to be locked in escrow</div></div>
            <div style="text-align:right;font-size:0.75rem;color:var(--muted);">Funds held securely<br>Released per milestone</div>
          </div>
        </div>
      </div>
      <button class="btn btn-amber" style="width:100%;padding:14px;" onclick="createProject()">🔒 Lock Funds & Create Project</button>
    </div>
  </div>
</div>

<div id="page-project" class="page">
  <div class="container"><div style="padding:40px 0 80px;"><div id="projectDetailContent"></div></div></div>
</div>

<script>
let currentUser = null, currentRole = 'client', milestoneCount = 0, currentProjectId = null, currentTab = 'projects';

async function api(path, method='GET', body=null) {
  const opts = { method, headers: {'Content-Type': 'application/json'}, credentials: 'include' };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  return r.json();
}

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const el = document.getElementById('page-' + name);
  if (el) { el.classList.add('active'); el.classList.add('animate-in'); }
  window.scrollTo(0, 0);
  if (name === 'dashboard') renderDashboard();
  if (name === 'newproject') initNewProject();
  updateStats();
}

function updateNav() {
  const nav = document.getElementById('authNav');
  if (currentUser) {
    nav.innerHTML = `<span style="color:var(--muted);font-size:0.75rem">${currentUser.name}</span>
      <a href="#" onclick="showPage('dashboard')">Dashboard</a>
      <a href="#" onclick="logout()">Sign Out</a>`;
  } else {
    nav.innerHTML = `<a href="#" onclick="showPage('auth')">Sign In</a>`;
  }
}

function toggleAuth(mode) {
  document.getElementById('loginForm').style.display = mode==='login' ? 'block' : 'none';
  document.getElementById('registerForm').style.display = mode==='register' ? 'block' : 'none';
}

function selectRole(role) {
  currentRole = role;
  document.getElementById('roleClient').classList.toggle('selected', role==='client');
  document.getElementById('roleFreelancer').classList.toggle('selected', role==='freelancer');
}

async function login() {
  const email = document.getElementById('loginEmail').value;
  const pass = document.getElementById('loginPass').value;
  const r = await api('/api/login', 'POST', {email, password: pass});
  if (r.ok) { currentUser = r.user; updateNav(); showPage('dashboard'); }
  else showAlert('authAlert', r.error, 'err');
}

async function register() {
  const name = document.getElementById('regName').value;
  const email = document.getElementById('regEmail').value;
  const pass = document.getElementById('regPass').value;
  const r = await api('/api/register', 'POST', {name, email, password: pass, role: currentRole});
  if (r.ok) { currentUser = r.user; updateNav(); showPage('dashboard'); }
  else showAlert('authAlert', r.error, 'err');
}

async function demoLogin(role) {
  const demos = { business: {email:'business@demo.com',password:'demo123'}, freelancer: {email:'freelancer@demo.com',password:'demo123'} };
  const r = await api('/api/login', 'POST', demos[role]);
  if (r.ok) { currentUser = r.user; updateNav(); showPage('dashboard'); }
  else {
    const names = {business:'Acme Corp',freelancer:'Alex Dev'}, roles = {business:'client',freelancer:'freelancer'};
    const cr = await api('/api/register', 'POST', {name:names[role], email:demos[role].email, password:demos[role].password, role:roles[role]});
    if (cr.ok) { currentUser = cr.user; updateNav(); showPage('dashboard'); }
  }
}

function logout() { currentUser = null; updateNav(); showPage('home'); }

async function renderDashboard() {
  if (!currentUser) { showPage('auth'); return; }
  document.getElementById('dashTitle').textContent = `Welcome, ${currentUser.name}`;
  document.getElementById('dashSubtitle').textContent = currentUser.role === 'client' ? 'Manage your projects and milestone approvals' : 'Track your work and earnings';
  document.getElementById('dashActions').innerHTML = currentUser.role === 'client' ? `<button class="btn btn-amber" onclick="showPage('newproject')">+ New Project</button>` : '';
  switchTab(currentTab);
}

async function switchTab(tab) {
  currentTab = tab;
  ['projects','activity','profile'].forEach(t => document.getElementById('tab-'+t).classList.toggle('active', t===tab));
  const el = document.getElementById('tabContent');
  if (tab === 'projects') await renderProjectsList(el);
  if (tab === 'activity') await renderActivity(el);
  if (tab === 'profile') renderProfile(el);
}

async function renderProjectsList(el) {
  const r = await api('/api/projects');
  const projects = r.projects || [];
  if (!projects.length) { el.innerHTML = `<div class="empty-state"><div class="icon">📋</div><div>${currentUser.role==='client'?'No projects yet. Create your first one.':'No projects assigned to you yet.'}</div></div>`; return; }
  el.innerHTML = projects.map(p => `
    <div class="card" style="cursor:pointer" onclick="viewProject('${p.id}')">
      <div class="card-header">
        <div><div class="card-title">${p.title}</div><div class="card-id">ID: ${p.id} · ${p.deadline||'No deadline'}</div></div>
        <span class="badge badge-${p.status}">${p.status}</span>
      </div>
      <div class="flex justify-between items-center">
        <div class="text-muted">${p.milestones.length} milestones</div>
        <div class="escrow-amount" style="font-size:1.2rem">$${p.total.toFixed(2)}</div>
      </div>
      <div class="progress-bar"><div class="progress-fill" style="width:${progressPct(p)}%"></div></div>
      <div class="text-muted mt-8">${completedCount(p)} of ${p.milestones.length} milestones complete</div>
    </div>`).join('');
}

function progressPct(p) { return !p.milestones.length ? 0 : (completedCount(p)/p.milestones.length*100).toFixed(0); }
function completedCount(p) { return p.milestones.filter(m=>m.status==='complete').length; }

async function renderActivity(el) {
  const r = await api('/api/activity');
  const logs = r.logs || [];
  if (!logs.length) { el.innerHTML = `<div class="empty-state"><div class="icon">📝</div><div>No activity yet.</div></div>`; return; }
  el.innerHTML = logs.map(l => `<div class="log-entry"><div class="log-time">${l.time.slice(11,16)}</div><div class="log-dot"></div><div class="log-text">${l.text}</div></div>`).join('');
}

function renderProfile(el) {
  el.innerHTML = `<div class="card" style="max-width:520px;">
    <div class="section-label" style="margin-bottom:20px;">Profile</div>
    <div class="form-group"><label>Name</label><input value="${currentUser.name}" readonly></div>
    <div class="form-group"><label>Email</label><input value="${currentUser.email}" readonly></div>
    <div class="form-group"><label>Role</label><input value="${currentUser.role==='client'?'Business / Client':'Freelancer'}" readonly></div>
    <div class="form-group"><label>Member ID</label><input value="${currentUser.id}" readonly></div>
    <div class="escrow-box" style="margin-top:8px;"><div class="escrow-amount" id="walletBal">Loading...</div><div class="escrow-meta">Available balance</div></div>
  </div>`;
  api('/api/balance').then(r => { document.getElementById('walletBal').textContent = '$'+(r.balance||0).toFixed(2); });
}

function initNewProject() {
  milestoneCount = 0;
  document.getElementById('milestoneInputs').innerHTML = '';
  document.getElementById('totalAmount').textContent = '$0.00';
  addMilestone(); addMilestone(); addMilestone();
  const d = new Date(); d.setDate(d.getDate()+30);
  document.getElementById('projDeadline').value = d.toISOString().split('T')[0];
}

function addMilestone() {
  milestoneCount++;
  const n = milestoneCount;
  const div = document.createElement('div');
  div.id = 'ms-'+n; div.className = 'milestone-item';
  div.innerHTML = `<span class="milestone-num">M${n}</span>
    <input type="text" placeholder="Milestone description" style="flex:1;margin-right:8px" id="msTitle-${n}" oninput="calcTotal()">
    <input type="number" placeholder="Amount" style="width:110px;margin-right:8px" id="msAmt-${n}" min="0" step="0.01" oninput="calcTotal()">
    <button class="btn btn-outline btn-sm" onclick="removeMilestone(${n})" style="padding:4px 8px;">✕</button>`;
  document.getElementById('milestoneInputs').appendChild(div);
}

function removeMilestone(n) { const el = document.getElementById('ms-'+n); if(el) el.remove(); calcTotal(); }

function calcTotal() {
  let total = 0;
  for (let i = 1; i <= milestoneCount; i++) { const a = parseFloat(document.getElementById('msAmt-'+i)?.value||0); if(!isNaN(a)) total+=a; }
  document.getElementById('totalAmount').textContent = '$'+total.toFixed(2);
}

async function createProject() {
  const title = document.getElementById('projTitle').value.trim();
  const desc = document.getElementById('projDesc').value.trim();
  const freelancerEmail = document.getElementById('projFreelancer').value.trim();
  const deadline = document.getElementById('projDeadline').value;
  const milestones = [];
  for (let i = 1; i <= milestoneCount; i++) {
    const t = document.getElementById('msTitle-'+i), a = document.getElementById('msAmt-'+i);
    if (t && a && t.value.trim() && parseFloat(a.value)>0) milestones.push({title:t.value.trim(), amount:parseFloat(a.value)});
  }
  if (!title||!freelancerEmail||!milestones.length) { showAlert('newProjectAlert','Please fill in title, freelancer email, and at least one milestone.','err'); return; }
  const r = await api('/api/projects','POST',{title,description:desc,freelancer_email:freelancerEmail,deadline,milestones});
  if (r.ok) { showPage('dashboard'); viewProject(r.project.id); }
  else showAlert('newProjectAlert', r.error, 'err');
}

async function viewProject(id) {
  currentProjectId = id;
  showPage('project');
  const r = await api('/api/projects/'+id);
  if (!r.ok) return;
  const p = r.project;
  const isClient = currentUser.role==='client', isFreelancer = currentUser.role==='freelancer';
  const milestonesHTML = p.milestones.map((m,i) => {
    let actions = '';
    if (isFreelancer && m.status==='pending') actions = `<button class="btn btn-amber btn-sm" onclick="submitMilestone('${p.id}','${m.id}')">Submit Work</button>`;
    if (isClient && m.status==='submitted') actions = `<button class="btn btn-green btn-sm" onclick="approveMilestone('${p.id}','${m.id}')">✓ Approve & Release</button> <button class="btn btn-outline btn-sm" onclick="rejectMilestone('${p.id}','${m.id}')">Revise</button>`;
    if (m.status==='complete') actions = `<span class="text-green" style="font-size:0.75rem">✓ Paid</span>`;
    const badgeClass = m.status==='pending'?'locked':m.status==='submitted'?'review':m.status==='complete'?'complete':'active';
    return `<div class="milestone-item" style="flex-wrap:wrap;gap:8px;">
      <span class="milestone-num">M${i+1}</span>
      <span class="milestone-title">${m.title}</span>
      <span class="badge badge-${badgeClass}">${m.status}</span>
      <span class="milestone-amount">$${m.amount.toFixed(2)}</span>
      <div class="milestone-actions">${actions}</div></div>`;
  }).join('');
  const contractText = generateContract(p);
  const acceptBtn = isFreelancer && p.status==='pending' ? `<button class="btn btn-amber" onclick="acceptProject('${p.id}')">✅ Accept Project & Contract</button>` : '';
  document.getElementById('projectDetailContent').innerHTML = `
    <div class="page-header">
      <div>
        <button class="btn btn-outline btn-sm" onclick="showPage('dashboard')" style="margin-bottom:12px">← Back</button>
        <h2>${p.title}</h2>
        <p class="text-muted">ID: ${p.id} · Created by ${p.client_name}</p>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <span class="badge badge-${p.status}" style="font-size:0.8rem;padding:6px 12px;">${p.status.toUpperCase()}</span>
        ${acceptBtn}
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 320px;gap:20px;align-items:start;">
      <div>
        <div class="card">
          <div class="section-label" style="margin-bottom:12px;">Project Brief</div>
          <p style="font-size:0.85rem;line-height:1.7;">${p.description||'No description provided.'}</p>
          ${p.deadline?`<p class="text-muted mt-16" style="font-size:0.75rem;">📅 Deadline: ${p.deadline}</p>`:''}
        </div>
        <div class="card">
          <div class="section-label" style="margin-bottom:16px;">Milestones</div>
          ${milestonesHTML}
          <div class="progress-bar" style="margin-top:20px;"><div class="progress-fill" style="width:${progressPct(p)}%"></div></div>
          <div class="text-muted mt-8">${completedCount(p)} of ${p.milestones.length} milestones complete</div>
        </div>
        <div class="card">
          <div class="section-label" style="margin-bottom:12px;">Contract</div>
          <div class="contract-preview">${contractText}</div>
          <a class="btn btn-outline btn-sm" style="margin-top:12px;display:inline-block;" href="/api/projects/${p.id}/contract">↓ Download Contract</a>
        </div>
      </div>
      <div>
        <div class="escrow-box">
          <div class="escrow-amount">$${p.total.toFixed(2)}</div>
          <div class="escrow-meta">Total project value</div>
          <hr style="border-color:var(--amber-dim);margin:16px 0;">
          <div class="flex justify-between text-muted" style="font-size:0.75rem;margin-bottom:6px;"><span>Released</span><span class="text-green">$${p.released.toFixed(2)}</span></div>
          <div class="flex justify-between text-muted" style="font-size:0.75rem;"><span>Locked</span><span class="text-amber">$${(p.total-p.released).toFixed(2)}</span></div>
        </div>
        <div class="card">
          <div class="section-label" style="margin-bottom:12px;">Parties</div>
          <div style="font-size:0.78rem;margin-bottom:12px;"><div class="text-muted">Client</div><div class="bold">${p.client_name}</div></div>
          <div style="font-size:0.78rem;">
            <div class="text-muted">Freelancer</div>
            <div class="bold">${p.freelancer_name||p.freelancer_email}</div>
            ${p.freelancer_accepted?'<span class="badge badge-complete" style="margin-top:4px;">Contract Signed</span>':'<span class="badge badge-pending" style="margin-top:4px;">Awaiting Acceptance</span>'}
          </div>
        </div>
        <div class="card">
          <div class="section-label" style="margin-bottom:12px;">Activity</div>
          <div id="projectLogs" style="font-size:0.78rem;">Loading...</div>
        </div>
      </div>
    </div>`;
  api('/api/activity?project='+id).then(r => {
    const logs = r.logs||[];
    document.getElementById('projectLogs').innerHTML = logs.slice(0,5).map(l=>`<div style="padding:8px 0;border-bottom:1px solid var(--border);"><div class="text-muted" style="font-size:0.65rem;">${l.time.slice(0,10)}</div><div>${l.text}</div></div>`).join('')||'<div class="text-muted">No activity yet.</div>';
  });
}

function generateContract(p) {
  return `SERVICE AGREEMENT
═══════════════════════════════════════

CONTRACT ID:   ${p.id}
DATE:          ${p.created_at.slice(0,10)}

PARTIES
───────────────────────────────────────
CLIENT:        ${p.client_name}
FREELANCER:    ${p.freelancer_name||p.freelancer_email}

PROJECT SCOPE
───────────────────────────────────────
Title: ${p.title}

${p.description||'[No description provided]'}

PAYMENT SCHEDULE (ESCROW)
───────────────────────────────────────
${p.milestones.map((m,i)=>`Milestone ${i+1}: ${m.title}\n  Amount: $${m.amount.toFixed(2)}\n  Status: ${m.status.toUpperCase()}`).join('\n\n')}

TOTAL VALUE: $${p.total.toFixed(2)}

TERMS & CONDITIONS
───────────────────────────────────────
1. ESCROW: Funds held until client approves each milestone.
2. IP TRANSFER: Rights transfer only upon full payment.
3. COMPLETION OBLIGATION: Freelancer must complete all milestones.
4. DISPUTE RESOLUTION: Platform mediation before legal action.
5. ABANDONMENT: 14-day no-submit = project abandonment; funds returned.

SIGNATURES
───────────────────────────────────────
Client: ${p.client_name}
${p.freelancer_accepted?'Freelancer: '+(p.freelancer_name||p.freelancer_email)+' [DIGITALLY SIGNED]':'Freelancer: [AWAITING SIGNATURE]'}
`;
}

async function acceptProject(id) { const r = await api('/api/projects/'+id+'/accept','POST'); if(r.ok) viewProject(id); }
async function submitMilestone(pId,mId) { const r = await api(`/api/projects/${pId}/milestones/${mId}/submit`,'POST'); if(r.ok) viewProject(pId); }
async function approveMilestone(pId,mId) { const r = await api(`/api/projects/${pId}/milestones/${mId}/approve`,'POST'); if(r.ok){viewProject(pId);updateStats();} }
async function rejectMilestone(pId,mId) { const r = await api(`/api/projects/${pId}/milestones/${mId}/reject`,'POST'); if(r.ok) viewProject(pId); }

async function updateStats() {
  const r = await api('/api/stats');
  if (r) { document.getElementById('statProjects').textContent=r.projects; document.getElementById('statEscrow').textContent='$'+r.escrow.toFixed(0); document.getElementById('statCompleted').textContent=r.completed; }
}

function showAlert(id, msg, type) {
  const el = document.getElementById(id);
  if (el) { el.innerHTML=`<div class="alert alert-${type}">${msg}</div>`; setTimeout(()=>el.innerHTML='',4000); }
}

updateStats(); updateNav();
</script>
</body>
</html>'''

# ─────────────────────────────────────────────
# REQUEST HANDLER
# ─────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"  {args[0]} {args[1]}")

    def get_session_user(self):
        cookie = self.headers.get('Cookie', '')
        for part in cookie.split(';'):
            part = part.strip()
            if part.startswith('session='):
                sid = part[8:]
                uid = SESSIONS.get(sid)
                if uid:
                    return DB['users'].get(uid)
        return None

    def set_session(self, user_id):
        sid = str(uuid.uuid4())
        SESSIONS[sid] = user_id
        return sid

    def send_json(self, data, status=200, cookie=None):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def send_html(self, html):
        body = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, filename='file.txt'):
        body = text.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_GET(self):
        path = self.path.split('?')[0]
        query = urllib.parse.parse_qs(self.path.split('?')[1] if '?' in self.path else '')
        u = self.get_session_user()

        if path == '/':
            self.send_html(HTML)

        elif path == '/api/projects':
            if not u: self.send_json({'ok': False, 'error': 'Not authenticated'}); return
            projects = []
            for p in DB['projects'].values():
                if u['role'] == 'client' and p['client_id'] == u['id']:
                    projects.append(p)
                elif u['role'] == 'freelancer' and p['freelancer_email'] == u['email']:
                    projects.append(p)
            projects.sort(key=lambda x: x['created_at'], reverse=True)
            self.send_json({'ok': True, 'projects': projects})

        elif path.startswith('/api/projects/') and path.endswith('/contract'):
            pid = path.split('/')[3]
            p = DB['projects'].get(pid)
            if not p: self.send_json({'error': 'Not found'}, 404); return
            text = f"SERVICE AGREEMENT — CONTRACT ID: {p['id']}\nGenerated: {now()[:10]}\n\n"
            text += f"CLIENT: {p['client_name']}\nFREELANCER: {p.get('freelancer_name') or p['freelancer_email']}\n\n"
            text += f"PROJECT: {p['title']}\n{p.get('description','')}\n\nMILESTONES:\n"
            for i, m in enumerate(p['milestones']):
                text += f"  {i+1}. {m['title']} — ${m['amount']:.2f} [{m['status'].upper()}]\n"
            text += f"\nTOTAL: ${p['total']:.2f} | RELEASED: ${p['released']:.2f}\n"
            text += "\nIP transfers on full completion. Governed by platform escrow terms."
            self.send_text(text, f"contract-{pid}.txt")

        elif path.startswith('/api/projects/'):
            if not u: self.send_json({'ok': False, 'error': 'Not authenticated'}); return
            pid = path.split('/')[3]
            p = DB['projects'].get(pid)
            if not p: self.send_json({'ok': False, 'error': 'Not found'}); return
            self.send_json({'ok': True, 'project': p})

        elif path == '/api/activity':
            if not u: self.send_json({'logs': []}); return
            proj_filter = query.get('project', [None])[0]
            logs = list(DB['transactions'])
            if proj_filter:
                logs = [l for l in logs if l.get('project_id') == proj_filter]
            elif u['role'] == 'client':
                ids = {pid for pid, p in DB['projects'].items() if p['client_id'] == u['id']}
                logs = [l for l in logs if not l.get('project_id') or l['project_id'] in ids]
            elif u['role'] == 'freelancer':
                ids = {pid for pid, p in DB['projects'].items() if p.get('freelancer_id') == u['id'] or p['freelancer_email'] == u['email']}
                logs = [l for l in logs if not l.get('project_id') or l['project_id'] in ids]
            logs.sort(key=lambda x: x['time'], reverse=True)
            self.send_json({'logs': logs[:30]})

        elif path == '/api/balance':
            if not u: self.send_json({'balance': 0}); return
            self.send_json({'balance': DB['users'][u['id']]['balance']})

        elif path == '/api/stats':
            active = sum(1 for p in DB['projects'].values() if p['status'] in ('active','pending'))
            escrow = sum(p['total'] - p['released'] for p in DB['projects'].values())
            completed = sum(sum(1 for m in p['milestones'] if m['status'] == 'complete') for p in DB['projects'].values())
            self.send_json({'projects': active, 'escrow': escrow, 'completed': completed})

        else:
            self.send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        path = self.path
        d = self.read_body()
        u = self.get_session_user()

        if path == '/api/register':
            if not d.get('email') or not d.get('password') or not d.get('name'):
                self.send_json({'ok': False, 'error': 'All fields required'}); return
            if any(x['email'] == d['email'] for x in DB['users'].values()):
                self.send_json({'ok': False, 'error': 'Email already registered'}); return
            uid = gen_id()
            user = {'id': uid, 'name': d['name'], 'email': d['email'],
                    'password': hash_pass(d['password']), 'role': d.get('role','client'),
                    'balance': 10000.0, 'created_at': now()}
            DB['users'][uid] = user
            sid = self.set_session(uid)
            log_activity(f"New user registered: {user['name']} ({user['role']})")
            safe = {k: v for k, v in user.items() if k != 'password'}
            self.send_json({'ok': True, 'user': safe}, cookie=f'session={sid}; Path=/')

        elif path == '/api/login':
            user = next((x for x in DB['users'].values()
                         if x['email'] == d.get('email') and x['password'] == hash_pass(d.get('password',''))), None)
            if not user: self.send_json({'ok': False, 'error': 'Invalid credentials'}); return
            sid = self.set_session(user['id'])
            safe = {k: v for k, v in user.items() if k != 'password'}
            self.send_json({'ok': True, 'user': safe}, cookie=f'session={sid}; Path=/')

        elif path == '/api/logout':
            self.send_json({'ok': True}, cookie='session=; Path=/; Max-Age=0')

        elif path == '/api/projects':
            if not u: self.send_json({'ok': False, 'error': 'Not authenticated'}); return
            if not d.get('title') or not d.get('milestones') or not d.get('freelancer_email'):
                self.send_json({'ok': False, 'error': 'Missing required fields'}); return
            milestones, total = [], 0
            for ms in d['milestones']:
                amt = float(ms['amount']); total += amt
                milestones.append({'id': gen_id(), 'title': ms['title'], 'amount': amt,
                                   'status': 'pending', 'submitted_at': None, 'approved_at': None})
            if total > u['balance']:
                self.send_json({'ok': False, 'error': f'Insufficient balance. Need ${total:.2f}, have ${u["balance"]:.2f}'}); return
            DB['users'][u['id']]['balance'] -= total
            pid = gen_id()
            freelancer = next((x for x in DB['users'].values() if x['email'] == d['freelancer_email']), None)
            project = {'id': pid, 'title': d['title'], 'description': d.get('description',''),
                       'client_id': u['id'], 'client_name': u['name'],
                       'freelancer_email': d['freelancer_email'],
                       'freelancer_id': freelancer['id'] if freelancer else None,
                       'freelancer_name': freelancer['name'] if freelancer else None,
                       'freelancer_accepted': False, 'deadline': d.get('deadline'),
                       'milestones': milestones, 'total': total, 'released': 0.0,
                       'status': 'pending', 'created_at': now()}
            DB['projects'][pid] = project
            log_activity(f"Project '{d['title']}' created by {u['name']} (${total:.2f} locked in escrow)", pid, u['id'])
            self.send_json({'ok': True, 'project': project})

        elif path.endswith('/accept'):
            pid = path.split('/')[3]
            p = DB['projects'].get(pid)
            if not p: self.send_json({'ok': False, 'error': 'Not found'}); return
            if not p['freelancer_id'] and u:
                p['freelancer_id'] = u['id']; p['freelancer_name'] = u['name']
            p['freelancer_accepted'] = True; p['status'] = 'active'
            log_activity(f"{u['name']} accepted project '{p['title']}' and signed the contract", pid, u['id'] if u else None)
            self.send_json({'ok': True, 'project': p})

        elif '/milestones/' in path and path.endswith('/submit'):
            parts = path.split('/')
            pid, mid = parts[3], parts[5]
            p = DB['projects'].get(pid)
            ms = next((m for m in p['milestones'] if m['id'] == mid), None) if p else None
            if not ms: self.send_json({'ok': False, 'error': 'Not found'}); return
            ms['status'] = 'submitted'; ms['submitted_at'] = now()
            log_activity(f"{u['name'] if u else 'Freelancer'} submitted milestone: '{ms['title']}' for review", pid)
            self.send_json({'ok': True})

        elif '/milestones/' in path and path.endswith('/approve'):
            parts = path.split('/')
            pid, mid = parts[3], parts[5]
            p = DB['projects'].get(pid)
            ms = next((m for m in p['milestones'] if m['id'] == mid), None) if p else None
            if not ms: self.send_json({'ok': False, 'error': 'Not found'}); return
            ms['status'] = 'complete'; ms['approved_at'] = now()
            p['released'] += ms['amount']
            if p['freelancer_id'] and p['freelancer_id'] in DB['users']:
                DB['users'][p['freelancer_id']]['balance'] += ms['amount']
            if all(m['status'] == 'complete' for m in p['milestones']):
                p['status'] = 'complete'
            log_activity(f"{u['name'] if u else 'Client'} approved '{ms['title']}' — ${ms['amount']:.2f} released", pid)
            self.send_json({'ok': True})

        elif '/milestones/' in path and path.endswith('/reject'):
            parts = path.split('/')
            pid, mid = parts[3], parts[5]
            p = DB['projects'].get(pid)
            ms = next((m for m in p['milestones'] if m['id'] == mid), None) if p else None
            if not ms: self.send_json({'ok': False, 'error': 'Not found'}); return
            ms['status'] = 'pending'; ms['submitted_at'] = None
            log_activity(f"{u['name'] if u else 'Client'} requested revisions on '{ms['title']}'", pid)
            self.send_json({'ok': True})

        else:
            self.send_json({'error': 'Not found'}, 404)


# ─────────────────────────────────────────────
# START SERVER
# ─────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"""
╔══════════════════════════════════════╗
║   🔒 LockWork — No dependencies!    ║
║   Open: http://localhost:{port}        ║
║   Press Ctrl+C to stop              ║
╚══════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
