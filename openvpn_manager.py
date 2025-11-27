#!/usr/bin/env python3
from flask import Flask, render_template_string, request, send_file, redirect, url_for, session
import subprocess
import tempfile
import hashlib
from functools import wraps
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-me-in-production')

# Configuration
VPN_DATA = '/opt/vpn-data'
PKI_ISSUED = f'{VPN_DATA}/pki/issued'
EASYRSA_PASSWORD = os.getenv('EASYRSA_PASSWORD', '')
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH', '')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# HTML Templates
LOGIN_TEMPLATE = '''<!DOCTYPE html><html><head><title>VPN Manager - Login</title><meta name="viewport" content="width=device-width, initial-scale=1"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.login-card{background:white;border-radius:16px;padding:48px 40px;width:100%;max-width:420px;box-shadow:0 20px 60px rgba(0,0,0,0.3);animation:slideUp 0.5s ease-out}@keyframes slideUp{from{opacity:0;transform:translateY(30px)}to{opacity:1;transform:translateY(0)}}.logo{text-align:center;margin-bottom:32px}.logo-icon{width:64px;height:64px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:32px;margin-bottom:16px}h1{font-size:28px;font-weight:600;color:#1a1a1a;text-align:center;margin-bottom:8px}.subtitle{color:#666;text-align:center;font-size:15px;margin-bottom:32px}.form-group{margin-bottom:24px}label{display:block;margin-bottom:8px;color:#333;font-weight:500;font-size:14px}input{width:100%;padding:14px 16px;border:2px solid #e5e7eb;border-radius:10px;font-size:15px;transition:all 0.3s;font-family:'Inter',sans-serif}input:focus{outline:none;border-color:#667eea;box-shadow:0 0 0 4px rgba(102,126,234,0.1)}.btn-login{width:100%;padding:14px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;border:none;border-radius:10px;font-size:16px;font-weight:600;cursor:pointer;transition:transform 0.2s,box-shadow 0.2s;font-family:'Inter',sans-serif}.btn-login:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(102,126,234,0.4)}.btn-login:active{transform:translateY(0)}.alert{padding:14px 16px;margin-bottom:24px;border-radius:10px;background:#fee;color:#c33;border:1px solid #fcc;font-size:14px;animation:shake 0.5s}@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-10px)}75%{transform:translateX(10px)}}</style></head><body><div class="login-card"><div class="logo"><div class="logo-icon">🔒</div></div><h1>VPN Manager</h1><p class="subtitle">Secure access to your certificates</p>{% if error %}<div class="alert">{{ error }}</div>{% endif %}<form method="POST" action="/login"><div class="form-group"><label>Username</label><input type="text" name="username" required autofocus placeholder="Enter your username"></div><div class="form-group"><label>Password</label><input type="password" name="password" required placeholder="Enter your password"></div><button type="submit" class="btn-login">Sign In</button></form></div></body></html>'''

MAIN_TEMPLATE = '''<!DOCTYPE html><html><head><title>VPN Certificate Manager</title><meta name="viewport" content="width=device-width, initial-scale=1"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#f8f9fa;color:#1a1a1a}.header{background:white;border-bottom:1px solid #e5e7eb;padding:20px 0;position:sticky;top:0;z-index:100;box-shadow:0 1px 3px rgba(0,0,0,0.05)}.container{max-width:1200px;margin:0 auto;padding:0 24px}.header-content{display:flex;justify-content:space-between;align-items:center}.logo{display:flex;align-items:center;gap:12px}.logo-icon{width:40px;height:40px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px}h1{font-size:20px;font-weight:600;color:#1a1a1a}.user-menu{display:flex;align-items:center;gap:16px}.user-info{color:#666;font-size:14px}.btn-logout{padding:8px 16px;background:#f3f4f6;color:#374151;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;text-decoration:none;transition:all 0.2s}.btn-logout:hover{background:#e5e7eb}.main-content{padding:32px 0}.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px;margin-bottom:32px}.stat-card{background:white;border-radius:12px;padding:24px;border:1px solid #e5e7eb;transition:transform 0.2s,box-shadow 0.2s}.stat-card:hover{transform:translateY(-2px);box-shadow:0 8px 16px rgba(0,0,0,0.1)}.stat-value{font-size:36px;font-weight:700;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}.stat-label{color:#666;font-size:14px;font-weight:500}.card{background:white;border-radius:12px;padding:24px;border:1px solid #e5e7eb;margin-bottom:24px}.card-header{display:flex;align-items:center;gap:12px;margin-bottom:20px}.card-icon{width:36px;height:36px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:18px}h2{font-size:18px;font-weight:600;color:#1a1a1a}.form-row{display:flex;gap:12px;align-items:flex-end}input[type="text"],.search-input{flex:1;padding:12px 16px;border:2px solid #e5e7eb;border-radius:10px;font-size:15px;transition:all 0.3s;font-family:'Inter',sans-serif}input[type="text"]:focus,.search-input:focus{outline:none;border-color:#667eea;box-shadow:0 0 0 4px rgba(102,126,234,0.1)}.btn{padding:12px 24px;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;transition:all 0.2s;font-family:'Inter',sans-serif;display:inline-flex;align-items:center;gap:8px}.btn-primary{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white}.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 16px rgba(102,126,234,0.3)}.btn-sm{padding:8px 16px;font-size:14px}.btn-download{background:#3b82f6;color:white}.btn-download:hover{background:#2563eb}.btn-revoke{background:#ef4444;color:white}.btn-revoke:hover{background:#dc2626}.alert{padding:14px 16px;border-radius:10px;margin-bottom:24px;font-size:14px;font-weight:500}.alert-success{background:#d1fae5;color:#065f46;border:1px solid #a7f3d0}.alert-error{background:#fee2e2;color:#991b1b;border:1px solid #fecaca}table{width:100%;border-collapse:separate;border-spacing:0}thead{background:#f9fafb}th{padding:12px 16px;text-align:left;font-size:13px;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;border-bottom:1px solid #e5e7eb}td{padding:16px;border-bottom:1px solid #f3f4f6;font-size:14px}tr:hover td{background:#f9fafb}.status-badge{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:600}.status-active{background:#d1fae5;color:#065f46}.status-revoked{background:#fee2e2;color:#991b1b}.actions{display:flex;gap:8px}.loading{display:none;padding:12px;background:#fef3c7;border-radius:8px;margin-top:12px;font-size:14px;color:#92400e}.search-box{margin-bottom:20px}</style><script>function filterTable(){const input=document.getElementById("searchInput");const filter=input.value.toUpperCase();const table=document.getElementById("certsTable");const rows=table.getElementsByTagName("tr");for(let i=1;i<rows.length;i++){const cells=rows[i].getElementsByTagName("td");if(cells.length>0){const text=cells[1].textContent||cells[1].innerText;rows[i].style.display=text.toUpperCase().indexOf(filter)>-1?"":"none"}}}function showLoading(){document.getElementById('loading').style.display='block';return true}function confirmRevoke(name){return confirm(`Are you sure you want to revoke certificate for "${name}"?\\n\\nThis action cannot be undone!`)}</script></head><body><div class="header"><div class="container"><div class="header-content"><div class="logo"><div class="logo-icon">🔒</div><h1>VPN Certificate Manager</h1></div><div class="user-menu"><span class="user-info">{{ username }}</span><a href="/logout" class="btn-logout">Sign Out</a></div></div></div></div><div class="main-content"><div class="container">{% if message %}<div class="alert alert-{{ message_type }}">{{ message }}</div>{% endif %}<div class="stats-grid"><div class="stat-card"><div class="stat-value">{{ total_certs }}</div><div class="stat-label">Active Certificates</div></div><div class="stat-card"><div class="stat-value">{{ revoked_count }}</div><div class="stat-label">Revoked Certificates</div></div></div><div class="card"><div class="card-header"><div class="card-icon">➕</div><h2>Create New Certificate</h2></div><form method="POST" action="/create" onsubmit="return showLoading()"><div class="form-row"><input type="text" name="client_name" placeholder="Enter client name (e.g., john-doe)" required pattern="[a-zA-Z0-9_.-]+" title="Only letters, numbers, underscore, dot and dash"><button type="submit" class="btn btn-primary">Create Certificate</button></div></form><div id="loading" class="loading">⏳ Creating certificate, please wait...</div></div><div class="card"><div class="card-header"><div class="card-icon">📋</div><h2>All Certificates ({{ total_certs }} active + {{ revoked_count }} revoked)</h2></div><div class="search-box"><input type="text" id="searchInput" class="search-input" onkeyup="filterTable()" placeholder="🔍 Search certificates..."></div><table id="certsTable"><thead><tr><th>#</th><th>Client Name</th><th>Created</th><th>Status</th><th>Actions</th></tr></thead><tbody>{% for i,cert in enumerate(certificates,1) %}<tr><td>{{ i }}</td><td><strong>{{ cert.name }}</strong></td><td><span style="color:#666;font-size:13px;">{{ cert.created }}</span></td><td>{% if cert.revoked %}<span class="status-badge status-revoked">❌ Revoked</span>{% else %}<span class="status-badge status-active">✅ Active</span>{% endif %}</td><td><div class="actions">{% if not cert.revoked %}<a href="/download/{{ cert.name }}" class="btn btn-download btn-sm">⬇️ Download</a><form method="POST" action="/revoke/{{ cert.name }}" style="display:inline;" onsubmit="return confirmRevoke('{{ cert.name }}')"><button type="submit" class="btn btn-revoke btn-sm">🗑️ Revoke</button></form>{% else %}<span style="color:#9ca3af;font-size:14px;">No actions</span>{% endif %}</div></td></tr>{% endfor %}</tbody></table></div></div></div></body></html>'''

def get_certificates():
    try:
        # Get list from ovpn_listclients which includes dates
        result = subprocess.run(
            ['sudo', 'docker', 'run', '-v', f'{VPN_DATA}:/etc/openvpn', '--rm', 'vpn', 'ovpn_listclients'],
            capture_output=True, text=True
        )
        
        certs_data = {}
        for line in result.stdout.strip().split('\n'):
            if line and not line.startswith('name,'):
                parts = line.split(',')
                if len(parts) >= 4:
                    name = parts[0]
                    begin_date = parts[1]
                    end_date = parts[2]
                    status = parts[3]
                    
                    # Parse date from "May 15 17:36:51 2025 GMT" to "2025-05-15"
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(begin_date.replace(' GMT', ''), '%b %d %H:%M:%S %Y')
                        formatted_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        formatted_date = begin_date
                    
                    certs_data[name] = {
                        'name': name,
                        'created': formatted_date,
                        'expires': end_date,
                        'revoked': status.upper() == 'REVOKED'
                    }
        
        return sorted(certs_data.values(), key=lambda x: x['name'])
    except Exception as e:
        # Fallback to old method
        try:
            result = subprocess.run(['sudo', 'ls', PKI_ISSUED], capture_output=True, text=True)
            certs = [c.replace('.crt', '') for c in result.stdout.strip().split('\n') if c and not c.startswith('3.')]
            
            index_result = subprocess.run(['sudo', 'cat', f'{VPN_DATA}/pki/index.txt'], capture_output=True, text=True)
            revoked_names = set()
            for line in index_result.stdout.split('\n'):
                if line.startswith('R'):
                    parts = line.split('\t')
                    if len(parts) >= 6:
                        revoked_names.add(parts[5].replace('/CN=', ''))
            
            return [{'name': cert, 'created': 'N/A', 'expires': 'N/A', 'revoked': cert in revoked_names} for cert in sorted(certs)]
        except:
            return []

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username == ADMIN_USERNAME and password_hash == ADMIN_PASSWORD_HASH:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        return render_template_string(LOGIN_TEMPLATE, error='Invalid username or password')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    certs = get_certificates()
    active_certs = [c for c in certs if not c['revoked']]
    revoked_certs = [c for c in certs if c['revoked']]
    
    return render_template_string(MAIN_TEMPLATE, 
                                 certificates=certs,
                                 total_certs=len(active_certs),
                                 revoked_count=len(revoked_certs),
                                 enumerate=enumerate,
                                 message=request.args.get('message'),
                                 message_type=request.args.get('type', 'success'),
                                 username=session.get('username'))

@app.route('/create', methods=['POST'])
@login_required
def create_client():
    client_name = request.form.get('client_name', '').strip()
    if not client_name:
        return redirect(url_for('index', message='Client name required', type='error'))
    
    try:
        process = subprocess.Popen([
            'sudo', 'docker', 'run', '-v', f'{VPN_DATA}:/etc/openvpn',
            '--rm', '-i', 'vpn', 'easyrsa', 'build-client-full', client_name, 'nopass'
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout, stderr = process.communicate(input=f'{EASYRSA_PASSWORD}\n')
        
        if process.returncode != 0:
            return redirect(url_for('index', message=f'Error: {stderr}', type='error'))
        
        return redirect(url_for('download_cert', client_name=client_name))
    except Exception as e:
        return redirect(url_for('index', message=f'Error: {str(e)}', type='error'))

@app.route('/revoke/<client_name>', methods=['POST'])
@login_required
def revoke_cert(client_name):
    try:
        # Step 1: Revoke the certificate
        process1 = subprocess.Popen([
            'sudo', 'docker', 'run', '-v', f'{VPN_DATA}:/etc/openvpn',
            '--rm', '-i', 'vpn', 'easyrsa', 'revoke', client_name
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout1, stderr1 = process1.communicate(input=f'yes\n{EASYRSA_PASSWORD}\n')
        
        # Check if already revoked
        if 'already revoked' in stderr1.lower() or 'already revoked' in stdout1.lower():
            return redirect(url_for('index', message=f'Certificate "{client_name}" is already revoked', type='error'))
        
        if process1.returncode != 0:
            return redirect(url_for('index', message=f'Error revoking: {stderr1}', type='error'))
        
        # Step 2: Generate CRL
        process2 = subprocess.Popen([
            'sudo', 'docker', 'run', '-v', f'{VPN_DATA}:/etc/openvpn',
            '--rm', '-i', 'vpn', 'easyrsa', 'gen-crl'
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        stdout2, stderr2 = process2.communicate(input=f'{EASYRSA_PASSWORD}\n')
        
        if process2.returncode != 0:
            return redirect(url_for('index', message=f'Error generating CRL: {stderr2}', type='error'))
        
        # Step 3: Copy CRL to the right location
        subprocess.run([
            'sudo', 'docker', 'exec', 'vpn', 'sh', '-c',
            'cp -f /etc/openvpn/pki/crl.pem /etc/openvpn/crl.pem && chmod 644 /etc/openvpn/crl.pem'
        ], check=True)
        
        return redirect(url_for('index', message=f'Certificate "{client_name}" revoked successfully!', type='success'))
    except Exception as e:
        return redirect(url_for('index', message=f'Error: {str(e)}', type='error'))

@app.route('/download/<client_name>')
@login_required
def download_cert(client_name):
    try:
        result = subprocess.run([
            'sudo', 'docker', 'run', '-v', f'{VPN_DATA}:/etc/openvpn',
            '--rm', 'vpn', 'ovpn_getclient', client_name
        ], capture_output=True, text=True, check=True)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ovpn', delete=False) as f:
            f.write(result.stdout)
            temp_path = f.name
        
        return send_file(temp_path, as_attachment=True, attachment_filename=f'{client_name}.ovpn', mimetype='application/x-openvpn-profile')
    except Exception as e:
        return redirect(url_for('index', message=f'Error: {str(e)}', type='error'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8082, debug=False)
