const login_btn=document.getElementById('login_btn')
const id_text=document.getElementById('email')
const pw_text=document.getElementById('password')
id_text.addEventListener('input',()=>{
    if (id_text.value===''){
        login_btn.disabled = true;
        submit_button.style.backgroundColor=''
    }
})