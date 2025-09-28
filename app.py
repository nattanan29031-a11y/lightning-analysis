 from flask import Flask, render_template, request, jsonify
import json
import random
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
CONFIG = {
    'TOWER_HEIGHTS': {
        '115kV_single': 26.35,
        '115kV_double': 28.83,
        '230kV_single': 32.00,
        '230kV_double': 42.54,
        '500kV_single': 41.12,
        '500kV_double': 65.00
    }
}

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>⚡ โปรแกรมจำลองฟ้าผ่าในแนวสายส่ง</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #333; }
            .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header { text-align: center; background: rgba(255,255,255,0.95); padding: 30px; border-radius: 15px; margin-bottom: 30px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
            .header h1 { font-size: 2.5em; color: #2c3e50; margin-bottom: 10px; }
            .header p { font-size: 1.2em; color: #666; }
            .section { background: rgba(255,255,255,0.95); margin-bottom: 25px; padding: 25px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
            h2 { color: #2c3e50; margin-bottom: 20px; font-size: 1.8em; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; font-weight: bold; color: #34495e; }
            select, input[type="text"] { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; transition: border-color 0.3s; }
            select:focus, input:focus { outline: none; border-color: #3498db; }
            .btn { background: #e74c3c; color: white; border: none; padding: 15px 30px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; transition: background 0.3s; }
            .btn:hover { background: #c0392b; }
            .status { margin-top: 15px; padding: 12px; border-radius: 5px; display: none; }
            .status.success { background: #d4edda; color: #155724; display: block; }
            .status.error { background: #f8d7da; color: #721c24; display: block; }
            .status.loading { background: #d1ecf1; color: #0c5460; display: block; }
            #resultsSection { display: none; }
            .summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }
            .summary-card { background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            .summary-card.high-risk { background: linear-gradient(135deg, #ff6b6b, #ee5a24); color: white; }
            .summary-card.prediction { background: linear-gradient(135deg, #4834d4, #686de0); color: white; }
            .summary-value { font-size: 2.5em; font-weight: bold; margin-top: 10px; }
            .chart-container { background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            .tower-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); background: white; }
            .risk-badge { padding: 8px 15px; border-radius: 20px; font-weight: bold; color: white; min-width: 80px; text-align: center; }
            .recommendations { background: #e8f5e8; padding: 20px; border-radius: 10px; border-left: 4px solid #27ae60; }
            .recommendations ul { list-style: none; padding: 0; }
            .recommendations li { background: white; padding: 12px; margin-bottom: 10px; border-radius: 8px; border-left: 4px solid #27ae60; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⚡ โปรแกรมจำลองฟ้าผ่าในแนวสายส่ง</h1>
                <p>ระบบคาดการณ์ความเสี่ยงฟ้าผ่าสำหรับเสาส่งไฟฟ้า (Web Application)</p>
            </div>

            <div class="section">
                <h2>🔬 การวิเคราะห์ความเสี่ยง</h2>
                <div class="form-group">
                    <label for="lineSelect">เลือกแนวสายส่ง:</label>
                    <select id="lineSelect">
                        <option value="">-- เลือกแนวสายส่ง --</option>
                        <option value="NPO1-UD2#12">NPO1-UD2#12 (115kV วงจรคู่)</option>
                        <option value="UD2-PHK">UD2-PHK (230kV วงจรเดี่ยว)</option>
                        <option value="PHK-BKK#1">PHK-BKK#1 (500kV วงจรเดี่ยว)</option>
                        <option value="BKK-SRT#12">BKK-SRT#12 (230kV วงจรคู่)</option>
                        <option value="SRT-ROI">SRT-ROI (115kV วงจรเดี่ยว)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="customLine">หรือระบุชื่อแนวสายส่ง:</label>
                    <input type="text" id="customLine" placeholder="เช่น NPO1-UD2#12, UD2-PHK">
                </div>
                
                <button class="btn" onclick="analyzeRisk()">🔍 เริ่มการวิเคราะห์</button>
                <div id="analysisStatus" class="status"></div>
            </div>

            <div id="resultsSection" class="section">
                <h2>📈 ผลการวิเคราะห์</h2>
                
                <div class="summary-cards">
                    <div class="summary-card">
                        <h3>จำนวนเสาทั้งหมด</h3>
                        <div class="summary-value" id="totalTowers">-</div>
                    </div>
                    <div class="summary-card high-risk">
                        <h3>เสาความเสี่ยงสูง</h3>
                        <div class="summary-value" id="highRiskTowers">-</div>
                    </div>
                    <div class="summary-card">
                        <h3>ฟ้าผ่าเฉลี่ย/ปี</h3>
                        <div class="summary-value" id="avgStrikes">-</div>
                    </div>
                    <div class="summary-card prediction">
                        <h3>คาดการณ์ปีหน้า</h3>
                        <div class="summary-value" id="nextYearPrediction">-</div>
                    </div>
                </div>

                <div class="chart-container">
                    <h3>📊 การกระจายความเสี่ยง</h3>
                    <canvas id="riskChart" width="400" height="200"></canvas>
                </div>

                <div id="towerList"></div>

                <div class="recommendations">
                    <h3>💡 คำแนะนำการป้องกัน</h3>
                    <ul id="recommendationsList"></ul>
                </div>
            </div>
        </div>

        <script>
            function analyzeRisk() {
                const lineSelect = document.getElementById('lineSelect').value;
                const customLine = document.getElementById('customLine').value;
                const lineName = customLine || lineSelect;
                const status = document.getElementById('analysisStatus');
                
                if (!lineName) {
                    showStatus(status, 'กรุณาเลือกหรือระบุชื่อแนวสายส่ง', 'error');
                    return;
                }
                
                showStatus(status, 'กำลังวิเคราะห์ข้อมูล...', 'loading');
                
                fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({line_name: lineName})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showStatus(status, 'วิเคราะห์เสร็จสิ้น!', 'success');
                        displayResults(data.data);
                    } else {
                        showStatus(status, data.message, 'error');
                    }
                })
                .catch(error => {
                    showStatus(status, 'เกิดข้อผิดพลาดในการเชื่อมต่อ', 'error');
                });
            }

            function displayResults(data) {
                document.getElementById('resultsSection').style.display = 'block';
                document.getElementById('totalTowers').textContent = data.statistics.totalTowers;
                document.getElementById('highRiskTowers').textContent = data.statistics.highRiskTowers;
                document.getElementById('avgStrikes').textContent = data.statistics.averageStrikesPerYear;
                document.getElementById('nextYearPrediction').textContent = data.predictions.nextYearExpectedStrikes;
                
                // Create risk chart
                const ctx = document.getElementById('riskChart').getContext('2d');
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(data.statistics.riskDistribution),
                        datasets: [{
                            data: Object.values(data.statistics.riskDistribution),
                            backgroundColor: ['#00FF00', '#90EE90', '#FFD700', '#FF8C00', '#FF0000']
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { position: 'bottom' } }
                    }
                });
                
                // Display towers
                const towerList = document.getElementById('towerList');
                towerList.innerHTML = '<h3>🏗️ ความเสี่ยงของเสาแต่ละต้น</h3>';
                
                data.riskAssessments.forEach(assessment => {
                    const towerDiv = document.createElement('div');
                    towerDiv.className = 'tower-item';
                    towerDiv.innerHTML = `
                        <div>
                            <h4>${assessment.tower.name}</h4>
                            <div>📍 ${assessment.coordinates.latitude.toFixed(4)}, ${assessment.coordinates.longitude.toFixed(4)}</div>
                        </div>
                        <div class="risk-badge" style="background-color: ${assessment.riskLevel.color};">
                            ${assessment.riskPercentage.toFixed(1)}%<br>
                            <small>${assessment.riskLevel.level}</small>
                        </div>
                    `;
                    towerList.appendChild(towerDiv);
                });
                
                // Display recommendations
                const recList = document.getElementById('recommendationsList');
                recList.innerHTML = '';
                data.predictions.recommendations.forEach(rec => {
                    const li = document.createElement('li');
                    li.textContent = rec;
                    recList.appendChild(li);
                });
                
                document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
            }

            function showStatus(element, message, type) {
                element.textContent = message;
                element.className = `status ${type}`;
            }
        </script>
    </body>
    </html>
    '''

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    line_name = data.get('line_name')
    
    # Generate demo data
    total_towers = random.randint(10, 25)
    high_risk_towers = random.randint(2, 8)
    avg_strikes = random.randint(15, 45)
    next_year = random.randint(18, 52)
    
    # Generate tower assessments
    assessments = []
    for i in range(total_towers):
        risk = random.uniform(10, 95)
        lat = 13.7563 + (random.random() - 0.5) * 0.1
        lng = 100.5018 + (random.random() - 0.5) * 0.1
        
        # Determine risk level
        if risk >= 80:
            level = {'level': 'สูงมาก', 'color': '#FF0000'}
        elif risk >= 60:
            level = {'level': 'สูง', 'color': '#FF8C00'}
        elif risk >= 40:
            level = {'level': 'ปานกลาง', 'color': '#FFD700'}
        elif risk >= 20:
            level = {'level': 'ต่ำ', 'color': '#90EE90'}
        else:
            level = {'level': 'ต่ำมาก', 'color': '#00FF00'}
        
        assessments.append({
            'tower': {'name': f'Tower T{i+1}'},
            'riskPercentage': round(risk, 2),
            'coordinates': {'latitude': lat, 'longitude': lng},
            'riskLevel': level
        })
    
    # Sort by risk level
    assessments.sort(key=lambda x: x['riskPercentage'], reverse=True)
    
    # Risk distribution
    risk_dist = {
        'ต่ำมาก': len([a for a in assessments if a['riskPercentage'] < 20]),
        'ต่ำ': len([a for a in assessments if 20 <= a['riskPercentage'] < 40]),
        'ปานกลาง': len([a for a in assessments if 40 <= a['riskPercentage'] < 60]),
        'สูง': len([a for a in assessments if 60 <= a['riskPercentage'] < 80]),
        'สูงมาก': len([a for a in assessments if a['riskPercentage'] >= 80])
    }
    
    return jsonify({
        'success': True,
        'data': {
            'lineName': line_name,
            'riskAssessments': assessments,
            'statistics': {
                'totalTowers': total_towers,
                'highRiskTowers': high_risk_towers,
                'averageStrikesPerYear': avg_strikes,
                'riskDistribution': risk_dist
            },
            'predictions': {
                'nextYearExpectedStrikes': next_year,
                'recommendations': [
                    'ติดตั้งระบบป้องกันฟ้าผ่าเพิ่มเติมสำหรับเสาความเสี่ยงสูง',
                    'เพิ่มการตรวจสอบและบำรุงรักษาอุปกรณ์ป้องกัน',
                    'วางแผนซ่อมบำรุงเชิงป้องกันก่อนฤดูฝน',
                    'พิจารณาปรับปรุงระบบกราวด์ในพื้นที่เสี่ยง',
                    'ติดตั้งเครื่องวัดฟ้าผ่าเพื่อเก็บข้อมูลเพิ่มเติม'
                ]
            }
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

