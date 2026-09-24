const express=require("express");
const session=require("express-session");
const http=require("http");
const path=require("path");
const fs=require("fs");
const multer=require("multer");
const {Server}=require("socket.io");

const app=express();
const server=http.createServer(app);
const io=new Server(server);

const DATA_FILE=path.join(__dirname,"data.json");
const UPLOAD_DIR=path.join(__dirname,"uploads");
fs.mkdirSync(UPLOAD_DIR,{recursive:true});

const upload=multer({
  dest:UPLOAD_DIR,
  limits:{fileSize:8*1024*1024},
  fileFilter:(req,file,cb)=>cb(null,/^image\/(jpeg|png|webp)$/.test(file.mimetype))
});

function initialData(){
  return {
    nextUserId:2,nextTestId:1,nextQuestionId:1,nextAttemptId:1,nextAnswerId:1,nextEventId:1,nextReviewId:1,
    users:[{id:1,username:"admin",password:"admin123",role:"admin"}],
    tests:[],questions:[],attempts:[],answers:[],events:[]
  };
}
if(!fs.existsSync(DATA_FILE)) fs.writeFileSync(DATA_FILE,JSON.stringify(initialData(),null,2));
let db=JSON.parse(fs.readFileSync(DATA_FILE,"utf8"));
function save(){fs.writeFileSync(DATA_FILE,JSON.stringify(db,null,2));}
function auth(role){
  return (req,res,next)=>{
    if(!req.session.user || (role && req.session.user.role!==role))
      return res.status(401).json({error:"Unauthorized"});
    next();
  };
}
app.use(express.json());
app.use(express.urlencoded({extended:true}));
app.use(session({
  secret:process.env.SESSION_SECRET||"concept-classes-secret",
  resave:false,saveUninitialized:false,
  cookie:{httpOnly:true,sameSite:"lax"}
}));
app.use(express.static(path.join(__dirname,"public")));
app.use("/uploads",express.static(UPLOAD_DIR));

app.post("/api/login",(req,res)=>{
  const selectedRole=req.body.role||"student";
  const u=db.users.find(x=>x.username===req.body.username&&x.password===req.body.password);
  if(!u)return res.status(401).json({error:"Invalid username or password"});
  const teacherRole=(u.role==="admin"||u.role==="teacher");
  if((selectedRole==="teacher"&&!teacherRole)||(selectedRole==="student"&&u.role!=="student"))
    return res.status(403).json({error:"This account is not registered for the selected portal."});
  req.session.user={id:u.id,username:u.username,role:u.role};
  res.json({user:req.session.user});
});
app.post("/api/logout",(req,res)=>req.session.destroy(()=>res.json({ok:true})));
app.get("/api/me",(req,res)=>res.json({user:req.session.user||null}));

app.post("/api/admin/student",auth("admin"),(req,res)=>{
  if(db.users.some(x=>x.username===req.body.username))
    return res.status(400).json({error:"Username already exists"});
  const u={id:db.nextUserId++,username:req.body.username,password:req.body.password,role:"student"};
  db.users.push(u);save();res.json({id:u.id});
});

app.post("/api/admin/tests",auth("admin"),(req,res)=>{
  const t={id:db.nextTestId++,title:req.body.title,subject:req.body.subject||"",
    class_name:req.body.className||"",duration:Number(req.body.duration)||30};
  db.tests.push(t);save();res.json({id:t.id});
});

app.post("/api/admin/tests/:id/questions",auth("admin"),(req,res)=>{
  const x=req.body;
  const q={id:db.nextQuestionId++,test_id:Number(req.params.id),question:x.question,
    option_a:x.a||"",option_b:x.b||"",option_c:x.c||"",option_d:x.d||"",
    correct:x.correct||"",marks:Number(x.marks)||1,negative:Number(x.negative)||0,
    type:x.type||"mcq",upload_window:Number(x.uploadWindow)||0};
  db.questions.push(q);save();res.json({id:q.id});
});

app.get("/api/admin/tests",auth("admin"),(req,res)=>{
  res.json(db.tests.slice().reverse().map(t=>({
    ...t,questions:db.questions.filter(q=>q.test_id===t.id)
  })));
});

// Lightweight endpoint used by the Add Question form.
app.get("/api/admin/tests/options",auth("admin"),(req,res)=>{
  res.json(db.tests.slice().reverse().map(t=>({id:t.id,title:t.title||`Examination ${t.id}`})));
});

app.get("/api/admin/results",auth("admin"),(req,res)=>{
  res.json(db.attempts.slice().reverse().map(a=>{
    const t=db.tests.find(x=>x.id===a.test_id),u=db.users.find(x=>x.id===a.student_id);
    return {...a,title:t?.title||"Unknown",username:u?.username||"Unknown"};
  }));
});

// Teacher paper-review view: returns submitted written answers and image paths.
app.get("/api/admin/papers",auth("admin"),(req,res)=>{
  const papers=db.attempts.filter(a=>a.status==="submitted").slice().reverse().map(a=>{
    const t=db.tests.find(x=>x.id===a.test_id),u=db.users.find(x=>x.id===a.student_id);
    const questions=db.questions.filter(q=>q.test_id===a.test_id).filter(q=>q.type==="written").map(q=>{
      const answer=db.answers.find(x=>x.attempt_id===a.id&&x.question_id===q.id);
      return {questionId:q.id,question:q.question,marks:q.marks,imageUrl:answer?.image_path?"/uploads/"+path.basename(answer.image_path):null,uploadedAt:answer?.uploaded_at||null};
    });
    return {attemptId:a.id,username:u?.username||"Unknown",title:t?.title||"Unknown",submittedAt:a.submitted_at,score:a.score,total:a.total,mcqScore:a.mcq_score||0,writtenScore:a.written_score||0,reviewStatus:a.review_status||"pending",resultPublished:!!a.result_published,questions};
  });
  res.json(papers);
});



app.post("/api/admin/papers/:attemptId/grade",auth("admin"),(req,res)=>{
  const a=db.attempts.find(x=>x.id===Number(req.params.attemptId));
  if(!a)return res.status(404).json({error:"Attempt not found"});
  const items=Array.isArray(req.body.items)?req.body.items:[];
  let writtenTotal=0;
  for(const item of items){
    const q=db.questions.find(x=>x.id===Number(item.questionId)&&x.test_id===a.test_id);
    if(!q || q.type!=="written") continue;
    const answer=db.answers.find(x=>x.attempt_id===a.id&&x.question_id===q.id);
    if(!answer) continue;
    const max=Number(q.marks)||0;
    const marks=Math.max(0,Math.min(max,Number(item.marks)||0));
    answer.awarded_marks=marks;
    answer.teacher_comment=String(item.comment||"").slice(0,1000);
    answer.checked_at=new Date().toISOString();
    writtenTotal+=marks;
  }
  const mcqTotal=db.questions.filter(q=>q.test_id===a.test_id&&q.type==="mcq").reduce((n,q)=>n+q.marks,0);
  a.written_score=writtenTotal;
  a.score=(Number(a.mcq_score)||0)+writtenTotal;
  a.review_status="checked";
  save();
  res.json({ok:true,score:a.score,total:a.total,reviewStatus:a.review_status});
});

app.post("/api/admin/results/:attemptId/publish",auth("admin"),(req,res)=>{
  const a=db.attempts.find(x=>x.id===Number(req.params.attemptId));
  if(!a)return res.status(404).json({error:"Attempt not found"});
  if(a.status!=="submitted")return res.status(400).json({error:"Exam has not been submitted"});
  const written=db.questions.filter(q=>q.test_id===a.test_id&&q.type==="written");
  const unchecked=written.some(q=>{const ans=db.answers.find(x=>x.attempt_id===a.id&&x.question_id===q.id);return ans && ans.awarded_marks===undefined;});
  if(unchecked)return res.status(400).json({error:"Please check all submitted written answers before publishing the result."});
  a.result_published=true;a.published_at=new Date().toISOString();a.review_status="published";save();
  res.json({ok:true});
});

app.get("/api/admin/papers/:attemptId",auth("admin"),(req,res)=>{
  const a=db.attempts.find(x=>x.id===Number(req.params.attemptId));
  if(!a)return res.status(404).json({error:"Attempt not found"});
  const t=db.tests.find(x=>x.id===a.test_id),u=db.users.find(x=>x.id===a.student_id);
  const questions=db.questions.filter(q=>q.test_id===a.test_id&&q.type==="written").map(q=>{
    const answer=db.answers.find(x=>x.attempt_id===a.id&&x.question_id===q.id);
    return {questionId:q.id,question:q.question,marks:q.marks,imageUrl:answer?.image_path?"/uploads/"+path.basename(answer.image_path):null,uploadedAt:answer?.uploaded_at||null,awardedMarks:answer?.awarded_marks,comment:answer?.teacher_comment||""};
  });
  res.json({attemptId:a.id,username:u?.username||"Unknown",title:t?.title||"Unknown",submittedAt:a.submitted_at,score:a.score,total:a.total,mcqScore:a.mcq_score||0,writtenScore:a.written_score||0,reviewStatus:a.review_status||"pending",resultPublished:!!a.result_published,questions});
});

app.get("/api/student/results",auth("student"),(req,res)=>{
  const results=db.attempts.filter(a=>a.student_id===req.session.user.id&&a.result_published).slice().reverse().map(a=>{
    const t=db.tests.find(x=>x.id===a.test_id);
    const questions=db.questions.filter(q=>q.test_id===a.test_id).map(q=>{
      const ans=db.answers.find(x=>x.attempt_id===a.id&&x.question_id===q.id);
      return {question:q.question,type:q.type,maxMarks:q.marks,awardedMarks:q.type==="mcq"?(ans?.answer===q.correct?q.marks:(ans?.answer?-(q.negative||0):0)):(ans?.awarded_marks||0),comment:ans?.teacher_comment||""};
    });
    return {attemptId:a.id,title:t?.title||"Unknown",subject:t?.subject||"",className:t?.class_name||"",score:a.score,total:a.total,mcqScore:a.mcq_score||0,writtenScore:a.written_score||0,publishedAt:a.published_at,questions};
  });
  res.json(results);
});

app.get("/api/tests",auth("student"),(req,res)=>res.json(db.tests));
app.get("/api/tests/:id",auth("student"),(req,res)=>{
  const t=db.tests.find(x=>x.id===Number(req.params.id));
  if(!t)return res.status(404).json({error:"Test not found"});
  const qs=db.questions.filter(q=>q.test_id===t.id).map(({correct,...q})=>q);
  res.json({test:t,questions:qs});
});

app.post("/api/attempts",auth("student"),(req,res)=>{
  const t=db.tests.find(x=>x.id===Number(req.body.testId));
  if(!t)return res.status(404).json({error:"Test not found"});
  const total=db.questions.filter(q=>q.test_id===t.id).reduce((n,q)=>n+q.marks,0);
  const a={id:db.nextAttemptId++,test_id:t.id,student_id:req.session.user.id,
    score:0,mcq_score:0,written_score:0,total,violations:0,status:"in_progress",review_status:"pending",result_published:false,started_at:new Date().toISOString(),submitted_at:null};
  db.attempts.push(a);save();res.json({attemptId:a.id,duration:t.duration});
});

app.post("/api/attempts/:id/event",auth("student"),(req,res)=>{
  const a=db.attempts.find(x=>x.id===Number(req.params.id)&&x.student_id===req.session.user.id);
  if(!a||a.status!=="in_progress")return res.status(400).json({error:"Invalid attempt"});
  db.events.push({id:db.nextEventId++,attempt_id:a.id,type:req.body.type,message:req.body.message,created_at:new Date().toISOString()});
  a.violations++;save();res.json({ok:true});
});

app.post("/api/attempts/:id/answer",auth("student"),upload.single("image"),(req,res)=>{
  const a=db.attempts.find(x=>x.id===Number(req.params.id)&&x.student_id===req.session.user.id);
  if(!a||a.status!=="in_progress")return res.status(400).json({error:"Invalid attempt"});
  const q=db.questions.find(x=>x.id===Number(req.body.questionId)&&x.test_id===a.test_id);
  if(!q)return res.status(404).json({error:"Question not found"});

  if(q.type==="written" && q.upload_window>0){
    const elapsed=(Date.now()-new Date(a.started_at).getTime())/60000;
    if(elapsed>q.upload_window){
      if(req.file) fs.unlinkSync(req.file.path);
      return res.status(400).json({error:"Upload window has expired"});
    }
  }

  const old=db.answers.find(x=>x.attempt_id===a.id&&x.question_id===q.id);
  if(old?.image_path && fs.existsSync(old.image_path)) fs.unlinkSync(old.image_path);
  db.answers=db.answers.filter(x=>!(x.attempt_id===a.id&&x.question_id===q.id));
  db.answers.push({
    id:db.nextAnswerId++,attempt_id:a.id,question_id:q.id,
    answer:req.body.answer||null,image_path:req.file?.path||null,
    uploaded_at:new Date().toISOString()
  });
  save();res.json({ok:true});
});

app.post("/api/attempts/:id/submit",auth("student"),(req,res)=>{
  const a=db.attempts.find(x=>x.id===Number(req.params.id)&&x.student_id===req.session.user.id);
  if(!a||a.status!=="in_progress")return res.status(400).json({error:"Already submitted"});
  const qs=db.questions.filter(q=>q.test_id===a.test_id);
  let score=0;
  for(const q of qs){
    const answer=db.answers.find(x=>x.attempt_id===a.id&&x.question_id===q.id);
    if(q.type==="mcq"){
      if(answer?.answer===q.correct)score+=q.marks;
      else if(answer?.answer)score-=q.negative;
    }
  }
  a.mcq_score=score;a.score=score;a.status="submitted";a.submitted_at=new Date().toISOString();save();
  res.json({score,total:a.total,violations:a.violations});
});

io.on("connection",socket=>socket.on("proctor_event",e=>console.log("PROCTOR",e)));
app.get("*",(req,res)=>res.sendFile(path.join(__dirname,"public/index.html")));

const PORT=process.env.PORT||3000;
server.listen(PORT,"0.0.0.0",()=>console.log(`Concept Classes Exam running on port ${PORT}`));