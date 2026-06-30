async function sendMessage(){

let input=document.getElementById("message");

let message=input.value;

if(message==="") return;

let chat=document.getElementById("chat");

chat.innerHTML+=`
<div class="user">${message}</div>
`;

input.value="";

chat.scrollTop=chat.scrollHeight;

let response=await fetch("/chat",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({

message:message

})

});

let data=await response.json();

chat.innerHTML+=`
<div class="bot">${marked.parse(data.response)}</div>
`;

chat.scrollTop=chat.scrollHeight;

}
