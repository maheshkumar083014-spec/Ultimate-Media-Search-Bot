<div class="welcome-section" style="text-align: left; margin-bottom: 20px;">
    <h1 id="greeting" style="font-size: 0.9rem; color: var(--primary); font-weight: 400; margin: 0;">Loading...</h1>
    <h2 style="font-size: 1.6rem; margin: 0; color: #fff;">{{ user_name }}! 👋</h2>
</div>

<script>
    // Time ke hisaab se greeting change karne ka script
    function setGreeting() {
        const hour = new Date().getHours();
        let welcomeText = "";
        if (hour < 12) welcomeText = "Good Morning,";
        else if (hour < 17) welcomeText = "Good Afternoon,";
        else welcomeText = "Good Evening,";
        
        document.getElementById('greeting').innerText = welcomeText;
    }
    setGreeting();
</script>
