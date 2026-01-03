// ------------------------
// Save student locally & sync
// ------------------------
window.saveStudent = async function() {
  const name = document.getElementById('name').value.trim();
  const attendance = document.getElementById('attendance').value.trim();
  const marks = document.getElementById('marks').value.trim();

  if (!name || !attendance || !marks) {
    alert('Please fill all fields!');
    return;
  }

  const student = { 
    name, 
    attendance: parseFloat(attendance), 
    marks: parseFloat(marks), 
    synced: false,
    risk: calculateRisk(parseFloat(attendance), parseFloat(marks))
  };

  // Save locally
  let students = JSON.parse(localStorage.getItem('students') || '[]');
  students.push(student);
  localStorage.setItem('students', JSON.stringify(students));

  updateStudentList();
  updateStatistics();

  // Clear form
  document.getElementById('name').value = '';
  document.getElementById('attendance').value = '';
  document.getElementById('marks').value = '';

  // Auto-sync if online
  if (navigator.onLine) await syncStudents();
}

// ------------------------
// Risk calculation (simple thresholds)
// ------------------------
function calculateRisk(attendance, marks) {
  if (attendance < 50 || marks < 50) return "High";
  if (attendance < 75 || marks < 75) return "Medium";
  return "Low";
}

// ------------------------
// Update dashboard
// ------------------------
function updateStudentList(filterQuery = "") {
  const students = JSON.parse(localStorage.getItem('students') || '[]');
  const list = document.getElementById('studentList');
  list.innerHTML = '';

  // Filter and reorder: matching search comes first
  const query = filterQuery.toLowerCase();
  const filtered = students.filter(s => s.name.toLowerCase().includes(query));
  const others = students.filter(s => !s.name.toLowerCase().includes(query));

  filtered.concat(others).forEach((s, i) => {
    const li = document.createElement('li');
    const color = s.risk === "High" ? "red" : s.risk === "Medium" ? "orange" : s.risk === "Low" ? "green" : "gray";
    li.innerHTML = `${i+1}. ${s.name} - Attendance: ${s.attendance}% | Marks: ${s.marks}% | Risk: <span style="color:${color}">${s.risk}</span>`;
    list.appendChild(li);
  });
}

// ------------------------
// Sync unsynced students to server
// ------------------------
async function syncStudents() {
  let students = JSON.parse(localStorage.getItem('students') || '[]');
  const unsynced = students.filter(s => !s.synced);

  for (let s of unsynced) {
    try {
      const res = await fetch("http://127.0.0.1:5001/api/v1/students", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(s)
      });

      if (!res.ok) {
        console.error("Sync failed with status:", res.status);
        continue;
      }

      const data = await res.json();
      s.synced = true;
      s.risk = data.risk || s.risk;
    } catch (err) {
      console.error("Sync failed:", err);
    }
  }

  localStorage.setItem('students', JSON.stringify(students));
  updateStudentList();
  updateStatistics();
}

// ------------------------
// Online/offline status
// ------------------------
function updateStatus() {
  const status = document.getElementById('status');
  if (navigator.onLine) {
    status.innerText = "Online ✅ (Auto Sync Enabled)";
    syncStudents();
  } else {
    status.innerText = "Offline ⚠️ (Saved Locally)";
  }
}

window.addEventListener("online", updateStatus);
window.addEventListener("offline", updateStatus);

// ------------------------
// Search filter
// ------------------------
const searchInput = document.getElementById('searchStudent');
if (searchInput) {
  searchInput.addEventListener('input', () => {
    const query = searchInput.value;
    updateStudentList(query);
  });
}

// ------------------------
// Dark/Light mode toggle
// ------------------------
const themeSelect = document.getElementById('themeSelect');
if (themeSelect) {
  themeSelect.addEventListener('change', () => {
    if (themeSelect.value === 'Dark') {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  });
}

// ------------------------
// Statistics tab update
// ------------------------
function updateStatistics() {
  const students = JSON.parse(localStorage.getItem('students') || '[]');
  const statsContent = document.getElementById('statsContent');
  if (!statsContent) return;

  if (students.length === 0) {
    statsContent.innerHTML = "No student data available.";
    return;
  }

  const total = students.length;
  const highRisk = students.filter(s => s.risk === "High").length;
  const mediumRisk = students.filter(s => s.risk === "Medium").length;
  const lowRisk = students.filter(s => s.risk === "Low").length;

  const avgAttendance = (students.reduce((a, s) => a + s.attendance, 0)/total).toFixed(1);
  const avgMarks = (students.reduce((a, s) => a + s.marks, 0)/total).toFixed(1);

  statsContent.innerHTML = `
    <p>Total Students: ${total}</p>
    <p>High Risk: ${highRisk} | Medium Risk: ${mediumRisk} | Low Risk: ${lowRisk}</p>
    <p>Average Attendance: ${avgAttendance}%</p>
    <p>Average Marks: ${avgMarks}%</p>
  `;
}

// ------------------------
// Initial load
// ------------------------
updateStatus();
updateStudentList();
updateStatistics();
