new Chart(document.getElementById("studentStatsChart"),{
  type:"bar",
  data:{
    labels:["Std 8","Std 9","Std 10"],
    datasets:[{
      data:[30,45,25],
      backgroundColor:"#3b82f6"
    }]
  },
  options:{
    plugins:{legend:{display:false}},
    scales:{y:{beginAtZero:true}}
  }
});

new Chart(document.getElementById("attendanceChart"),{
  type:"line",
  data:{
    labels:["Mon","Tue","Wed","Thu","Fri"],
    datasets:[{
      data:[75,82,78,85,90],
      borderColor:"#22c55e",
      tension:.4
    }]
  }
});
