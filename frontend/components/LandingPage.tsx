"use client";
import { useEffect } from "react";

export default function LandingPage() {

  useEffect(() => {
    const els = document.querySelectorAll(".fade-up");
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            (e.target as HTMLElement).style.opacity = "1";
            (e.target as HTMLElement).style.transform = "translateY(0)";
          }
        });
      },
      { threshold: 0.1 }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
        *{margin:0;padding:0;box-sizing:border-box}
        :root{
          --bg:#06080f;--bg2:#0c1020;--surface:#111828;--surface2:#1a2240;
          --border:#1e2a4a;--text:#e2e8f0;--muted:#7b8baa;
          --blue:#3b82f6;--blue-glow:#3b82f640;--cyan:#06d6a0;--cyan-glow:#06d6a040;
          --red:#ef4444;--amber:#f59e0b;--green:#22c55e;
          --grad:linear-gradient(135deg,#3b82f6,#06d6a0);
        }
        html{scroll-behavior:smooth}
        body{margin:0;padding:0}
        .lr{font-family:'Plus Jakarta Sans',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;line-height:1.6}
        a{color:inherit;text-decoration:none}
        .lr::after{content:'';position:fixed;inset:0;z-index:9999;pointer-events:none;opacity:.03;
          background:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
        .lc{max-width:1140px;margin:0 auto;padding:0 24px}
        .mono{font-family:'JetBrains Mono',monospace}
        .gt{background:var(--grad);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
        .btn{display:inline-flex;align-items:center;gap:8px;padding:14px 32px;border-radius:12px;font-weight:700;font-size:15px;cursor:pointer;border:none;transition:all .3s;text-decoration:none}
        .btn-p{background:var(--grad);color:#fff !important;box-shadow:0 4px 30px var(--blue-glow)}
        .btn-p:hover{transform:translateY(-2px);box-shadow:0 8px 40px var(--blue-glow)}
        .btn-o{background:transparent;color:var(--text) !important;border:1.5px solid var(--border)}
        .btn-o:hover{border-color:var(--blue);color:var(--blue) !important}
        .fade-up{opacity:0;transform:translateY(32px);transition:opacity 0.7s ease,transform 0.7s ease}
        .fade-up.d1{transition-delay:.1s}.fade-up.d2{transition-delay:.2s}.fade-up.d3{transition-delay:.3s}
        .fade-up.d4{transition-delay:.4s}.fade-up.d5{transition-delay:.5s}
        .hi{opacity:0;transform:translateY(24px);animation:hIn 0.8s ease forwards}
        .hi.d1{animation-delay:.1s}.hi.d2{animation-delay:.2s}.hi.d3{animation-delay:.3s}
        .hi.d4{animation-delay:.4s}.hi.d5{animation-delay:.5s}
        @keyframes hIn{to{opacity:1;transform:translateY(0)}}
        @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}}
        @keyframes pglow{0%,100%{opacity:.4}50%{opacity:.8}}
        @keyframes bgrow{to{width:95%}}

        /* Navbar */
        .nav{position:fixed;top:0;width:100%;z-index:100;padding:16px 0;backdrop-filter:blur(20px);background:rgba(6,8,15,.85);border-bottom:1px solid rgba(30,42,74,.5)}
        .nav-i{display:flex;align-items:center;justify-content:space-between}
        .logo{display:flex;align-items:center;gap:10px;font-weight:800;font-size:20px}
        .logo img{width:36px;height:36px;border-radius:8px;object-fit:cover}
        .nlinks{display:flex;gap:32px;align-items:center}
        .nlinks a{font-size:14px;font-weight:500;color:var(--muted);transition:color .2s}
        .nlinks a:hover{color:var(--text)}

        /* Hero */
        .hero{padding:160px 0 100px;position:relative;text-align:center;overflow:hidden}
        .hglow{position:absolute;top:-200px;left:50%;transform:translateX(-50%);width:800px;height:800px;background:radial-gradient(circle,var(--blue-glow) 0%,transparent 70%);pointer-events:none;animation:pglow 4s ease-in-out infinite}
        .ol{letter-spacing:3px;font-size:12px;font-weight:700;color:var(--cyan);text-transform:uppercase;margin-bottom:20px}
        .hero h1{font-size:clamp(36px,5.5vw,64px);font-weight:800;line-height:1.1;margin-bottom:24px;max-width:800px;margin-left:auto;margin-right:auto}
        .hsub{font-size:18px;color:var(--muted);max-width:600px;margin:0 auto 40px;line-height:1.7}
        .hbtns{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}
        .srow{display:flex;gap:48px;justify-content:center;margin-top:60px;flex-wrap:wrap}
        .snum{font-size:36px;font-weight:800}
        .slbl{font-size:13px;color:var(--muted);margin-top:4px}
        .nc{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:32px;max-width:480px;margin:60px auto 0;position:relative;animation:float 5s ease-in-out infinite;box-shadow:0 20px 60px rgba(0,0,0,.5)}
        .prob{font-size:48px;font-weight:800;color:var(--red)}
        .plbl{font-size:13px;color:var(--muted);margin-bottom:16px}
        .bbg{height:8px;background:var(--surface2);border-radius:4px;overflow:hidden;margin-bottom:20px}
        .bfill{height:100%;border-radius:4px;background:linear-gradient(90deg,var(--amber),var(--red));width:0;animation:bgrow 2s ease .5s both}
        .ri{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:14px}
        .ri:last-of-type{border:none}
        .rdot{width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:8px}

        /* Section heading */
        .sl{text-align:center;margin-bottom:60px}
        .sl h2{font-size:clamp(28px,4vw,44px);font-weight:800}
        .sl p{color:var(--muted);max-width:500px;margin:12px auto 0;font-size:16px}

        /* Features */
        .features{padding:120px 0}
        .fg{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}
        .fc{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:32px;transition:all .3s;position:relative;overflow:hidden}
        .fc:hover{border-color:var(--blue);transform:translateY(-4px);box-shadow:0 12px 40px rgba(59,130,246,.1)}
        .fi{width:48px;height:48px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px;margin-bottom:16px}
        .fc h3{font-size:18px;font-weight:700;margin-bottom:8px}
        .fc p{font-size:14px;color:var(--muted);line-height:1.7}
        .ftag{position:absolute;top:16px;right:16px;font-size:10px;font-weight:700;padding:4px 10px;border-radius:6px;letter-spacing:.5px}

        /* How */
        .how{padding:120px 0;background:var(--bg2)}
        .steps{display:grid;grid-template-columns:repeat(3,1fr);gap:32px;margin-top:40px}
        .step{text-align:center;padding:40px 24px}
        .sn{width:56px;height:56px;border-radius:50%;background:var(--grad);display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;color:#fff;margin:0 auto 20px;box-shadow:0 4px 20px var(--blue-glow)}
        .step h3{font-size:18px;font-weight:700;margin-bottom:8px}
        .step p{font-size:14px;color:var(--muted)}

        /* Pricing */
        .pricing{padding:120px 0}
        .pg{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;max-width:960px;margin:40px auto 0}
        .pc{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:36px;text-align:center;transition:all .3s;position:relative}
        .pc.pop{border-color:var(--blue);box-shadow:0 0 40px var(--blue-glow)}
        .pc.pop::before{content:'MOST POPULAR';position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:var(--grad);color:#fff;font-size:11px;font-weight:700;padding:4px 16px;border-radius:20px;letter-spacing:1px}
        .pname{font-size:14px;font-weight:600;color:var(--muted);margin-bottom:8px}
        .amt{font-size:42px;font-weight:800;margin-bottom:4px}
        .per{font-size:13px;color:var(--muted);margin-bottom:24px}
        .fl{text-align:left;margin-bottom:28px;list-style:none;padding:0}
        .fl li{display:flex;align-items:center;gap:10px;padding:8px 0;font-size:14px;color:var(--muted)}
        .fl li::before{content:'✓';color:var(--cyan);font-weight:700;font-size:14px;flex-shrink:0}

        /* Languages */
        .langs{padding:100px 0;background:var(--bg2);text-align:center}
        .lcards{display:flex;gap:24px;justify-content:center;margin-top:40px;flex-wrap:wrap}
        .lcard{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:32px 40px;text-align:center;min-width:200px;transition:all .3s}
        .lcard:hover{border-color:var(--cyan);transform:translateY(-4px)}
        .flag{font-size:36px;margin-bottom:12px}
        .lcard h3{font-size:16px;font-weight:700;margin-bottom:4px}
        .lcard p{font-size:13px;color:var(--muted)}
        .lsamp{margin-top:8px;font-size:12px;color:var(--cyan);background:var(--surface2);padding:8px 12px;border-radius:8px;display:inline-block}

        /* Testimonials */
        .trust{padding:100px 0}
        .tg{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:40px}
        .tc{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:28px}
        .tq{font-size:15px;color:var(--muted);line-height:1.7;margin-bottom:16px;font-style:italic}
        .ta{font-size:13px;font-weight:600}
        .tr{font-size:12px;color:var(--muted)}

        /* Team */
        .team{padding:100px 0;background:var(--bg2);text-align:center}
        .team-grid{display:flex;gap:32px;justify-content:center;margin-top:48px;flex-wrap:wrap}
        .team-card{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:40px 36px;text-align:center;width:300px;transition:all .3s;position:relative;overflow:hidden}
        .team-card:hover{border-color:var(--blue);transform:translateY(-6px);box-shadow:0 16px 48px rgba(59,130,246,.15)}
        .team-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--grad)}
        .team-avatar{width:76px;height:76px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:30px;font-weight:800;color:#fff;margin:0 auto 18px;box-shadow:0 4px 24px var(--blue-glow)}
        .team-name{font-size:20px;font-weight:800;margin-bottom:4px}
        .team-role{font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--cyan);margin-bottom:14px;padding:4px 12px;background:rgba(6,214,160,.1);border-radius:20px;display:inline-block}
        .team-bio{font-size:13px;color:var(--muted);line-height:1.8;margin-bottom:22px}
        .team-links{display:flex;flex-direction:column;gap:10px}
        .team-link{display:flex;align-items:center;gap:10px;padding:11px 16px;border-radius:10px;background:var(--surface2);border:1px solid var(--border);font-size:13px;color:var(--muted);transition:all .2s;text-decoration:none;word-break:break-all}
        .team-link:hover{border-color:var(--cyan);color:var(--cyan);background:rgba(6,214,160,.05)}

        /* CTA */
        .cta{padding:100px 0;text-align:center;position:relative}
        .cta::before{content:'';position:absolute;bottom:0;left:50%;transform:translateX(-50%);width:600px;height:400px;background:radial-gradient(circle,var(--cyan-glow) 0%,transparent 70%);pointer-events:none}
        .cta h2{font-size:clamp(28px,4vw,44px);font-weight:800;margin-bottom:16px}
        .csub{color:var(--muted);max-width:500px;margin:0 auto 32px;font-size:16px}

        /* Footer */
        .foot{padding:48px 0;border-top:1px solid var(--border);text-align:center;font-size:13px;color:var(--muted)}
        .foot-links{display:flex;gap:24px;justify-content:center;flex-wrap:wrap;margin-top:12px}
        .foot-links a{color:var(--blue);transition:opacity .2s}
        .foot-links a:hover{opacity:.7}
        .foot-founders{display:flex;gap:40px;justify-content:center;flex-wrap:wrap;margin-top:24px;padding-top:20px;border-top:1px solid var(--border)}
        .founder-item{display:flex;flex-direction:column;gap:6px;align-items:center}
        .founder-label{font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted)}
        .founder-name{font-size:13px;font-weight:600;color:var(--text)}
        .founder-contacts{display:flex;gap:12px;align-items:center;flex-wrap:wrap;justify-content:center}
        .founder-contacts a{color:var(--cyan);font-size:12px;transition:opacity .2s}
        .founder-contacts a:hover{opacity:.7}

        @media(max-width:768px){
          .nlinks{display:none}
          .steps,.pg,.tg{grid-template-columns:1fr}
          .srow{gap:24px}
          .fg{grid-template-columns:1fr}
          .lcards{flex-direction:column;align-items:center}
          .team-grid{flex-direction:column;align-items:center}
          .team-card{width:100%;max-width:340px}
          .foot-founders{flex-direction:column;gap:24px;align-items:center}
        }
      `}</style>

      <div className="lr">

        {/* NAVBAR */}
        <nav className="nav">
          <div className="lc nav-i">
            <a href="#" className="logo">
              <img src="/logo.png" alt="AuditAI Logo" />
              <span>Audit<span className="gt">AI</span></span>
            </a>
            <div className="nlinks">
              <a href="#features">Features</a>
              <a href="#how">How it Works</a>
              <a href="#pricing">Pricing</a>
              <a href="#languages">Languages</a>
              <a href="#team">Team</a>
              <a href="/signup" className="btn btn-p" style={{padding:"10px 24px",fontSize:"13px",borderRadius:"10px"}}>Start Free →</a>
            </div>
          </div>
        </nav>

        {/* HERO */}
        <section className="hero">
          <div className="hglow" />
          <div className="lc">
            <div className="ol hi">India's First GST Notice Predictor</div>
            <h1 className="hi d1">Stop GST Notices <span className="gt">Before They Arrive</span></h1>
            <p className="hsub hi d2">
              Upload Excel → AI runs 10 audit checks in 2 minutes →
              Predicts notice probability → Fix-it reports in Hindi, English & Marathi
            </p>
            <div className="hbtns hi d3">
              <a href="/signup" className="btn btn-p">Start Free Audit →</a>
              <a href="#how" className="btn btn-o">See How it Works</a>
            </div>
            <div className="srow hi d4">
              {[{num:"10+",lbl:"Audit Checks"},{num:"2 min",lbl:"Per Audit"},{num:"3",lbl:"Languages"},{num:"95%",lbl:"Detection Rate"}].map(s=>(
                <div key={s.lbl} style={{textAlign:"center"}}>
                  <div className="snum gt">{s.num}</div>
                  <div className="slbl">{s.lbl}</div>
                </div>
              ))}
            </div>
            <div className="nc" style={{opacity:1,transform:"none"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start"}}>
                <div>
                  <div className="plbl">GST Notice Probability</div>
                  <div className="prob">95%</div>
                </div>
                <span style={{display:"inline-flex",padding:"6px 14px",borderRadius:"20px",fontSize:"12px",fontWeight:600,background:"#ef444420",color:"var(--red)"}}>VERY HIGH RISK</span>
              </div>
              <div className="bbg"><div className="bfill" /></div>
              {[{lbl:"Tax Computation Error",pct:"54%",c:"var(--red)"},{lbl:"Fraud Detection",pct:"15%",c:"var(--amber)"},{lbl:"Filing Non-Compliance",pct:"10%",c:"var(--blue)"}].map(r=>(
                <div key={r.lbl} className="ri">
                  <span><span className="rdot" style={{background:r.c}} />{r.lbl}</span>
                  <span className="mono" style={{color:r.c}}>{r.pct}</span>
                </div>
              ))}
              <div style={{marginTop:16,padding:12,background:"var(--surface2)",borderRadius:10,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                <span style={{fontSize:13,color:"var(--muted)"}}>If you fix all →</span>
                <span style={{fontSize:13}}>
                  <span style={{color:"var(--red)",textDecoration:"line-through"}}>95%</span>{" "}
                  <span style={{fontWeight:700,color:"var(--green)"}}>→ 28%</span>
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section className="features" id="features">
          <div className="lc">
            <div className="sl">
              <div className="ol fade-up">Powerful Features</div>
              <h2 className="fade-up d1">Everything a CA Needs, <span className="gt">In One Tool</span></h2>
              <p className="fade-up d2">Built by someone who understands GST data — tested on real client files</p>
            </div>
            <div className="fg">
              {[
                {icon:"🔮",bg:"#ef444420",tag:{text:"UNIQUE",bg:"#ef444420",c:"var(--red)"},  title:"GST Notice Predictor",    desc:"AI predicts the probability of receiving a GST notice (ASMT-10, DRC-01, ADT-01). Shows exact risk areas and 'what-if' analysis — fix issues and see probability drop."},
                {icon:"🔍",bg:"#3b82f620",tag:null,                                            title:"10+ Smart Audit Checks",  desc:"Tax type mismatch, missing invoices in GSTR-1, GSTR-2B gaps, amount mismatches, duplicates, invalid GSTIN — all detected automatically."},
                {icon:"📊",bg:"#06d6a020",tag:null,                                            title:"Risk Score Dashboard",    desc:"Every client gets a compliance score (0-100) with severity breakdown. Track all clients from one dashboard."},
                {icon:"🌐",bg:"#f59e0b20",tag:{text:"UNIQUE",bg:"#06d6a020",c:"var(--cyan)"}, title:"Hindi & Marathi Reports", desc:"Generate audit reports in English, Hindi, or Marathi. Issue descriptions, fix steps, legal references — all in your preferred language."},
                {icon:"📋",bg:"#8b5cf620",tag:null,                                            title:"Professional PDF Reports",desc:"Download audit reports with compliance score, ITC at risk, legal references, penalty calculations, and step-by-step fix instructions."},
                {icon:"🏢",bg:"#ec489920",tag:null,                                            title:"8 Business Sectors",     desc:"Sector-specific checks for Healthcare, Manufacturing, Retail, IT Services, Real Estate, Restaurant, Export/Import."},
                {icon:"📂",bg:"#3b82f620",tag:null,                                            title:"Any Excel Format",        desc:"Smart column mapper with 200+ aliases. Works with Tally, Busy, Zoho, Marg ERP, SAP, GSTN portal downloads."},
                {icon:"🔒",bg:"#06d6a020",tag:null,                                            title:"Bank-Grade Security",     desc:"AES-256 encryption for all GSTIN data. Row-level security in Supabase. Asia Pacific data storage."},
              ].map((f,i)=>(
                <div key={f.title} className={`fc fade-up d${(i%4)+1}`}>
                  {f.tag && <div className="ftag" style={{background:f.tag.bg,color:f.tag.c}}>{f.tag.text}</div>}
                  <div className="fi" style={{background:f.bg}}>{f.icon}</div>
                  <h3>{f.title}</h3>
                  <p>{f.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section className="how" id="how">
          <div className="lc">
            <div className="sl">
              <div className="ol fade-up">Simple Process</div>
              <h2 className="fade-up d1">Audit Done in <span className="gt">3 Easy Steps</span></h2>
            </div>
            <div className="steps">
              {[
                {n:"1",title:"Upload Excel Files",      desc:"Upload your client's Sales Register + Purchase Register. Works with any accounting software — Tally, Busy, Zoho, or manual Excel."},
                {n:"2",title:"AI Runs 10+ Checks",      desc:"In under 2 minutes, our engine checks tax type, GSTIN validity, missing invoices, amount mismatches, duplicates, and sector-specific rules."},
                {n:"3",title:"Get Report + Prediction", desc:"Download a professional PDF with compliance score, notice probability, fix steps, and legal references — in English, Hindi, or Marathi."},
              ].map((s,i)=>(
                <div key={s.n} className={`step fade-up d${i+1}`}>
                  <div className="sn">{s.n}</div>
                  <h3>{s.title}</h3>
                  <p>{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* PRICING */}
        <section className="pricing" id="pricing">
          <div className="lc">
            <div className="sl">
              <div className="ol fade-up">Simple Pricing</div>
              <h2 className="fade-up d1">Plans That <span className="gt">Fit Your Practice</span></h2>
              <p className="fade-up d2">Start free. Upgrade when you need more.</p>
            </div>
            <div className="pg">
              {[
                {plan:"FREE",amt:"₹0",    per:"forever",   pop:false,feats:["3 audits per month","All 10+ audit checks","Notice probability","PDF report download","1 language (English)"],                                                               cta:"Get Started",  s:"o"},
                {plan:"PRO", amt:"₹999",  per:"per month", pop:true, feats:["Unlimited audits","All 10+ audit checks","Notice predictor + What-if","Hindi + Marathi reports","Notice reply generator","Client management","Priority support"],           cta:"Start Pro →",  s:"p"},
                {plan:"FIRM",amt:"₹2,499",per:"per month", pop:false,feats:["Everything in Pro","5 team members","Bulk audit (50+ clients)","Supplier trust scores","Custom branding on PDF","API access","Dedicated support"],                          cta:"Contact Sales", s:"o"},
              ].map((p,i)=>(
                <div key={p.plan} className={`pc fade-up d${i+1}${p.pop?" pop":""}`}>
                  <div className="pname">{p.plan}</div>
                  <div className={`amt${p.pop?" gt":""}`}>{p.amt}</div>
                  <div className="per">{p.per}</div>
                  <ul className="fl">{p.feats.map(f=><li key={f}>{f}</li>)}</ul>
                  <a href="/signup" className={`btn btn-${p.s}`} style={{width:"100%",justifyContent:"center"}}>{p.cta}</a>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* LANGUAGES */}
        <section className="langs" id="languages">
          <div className="lc">
            <div className="sl">
              <div className="ol fade-up">Multi-Language</div>
              <h2 className="fade-up d1">Reports in <span className="gt">Your Language</span></h2>
              <p className="fade-up d2">First GST audit tool with Marathi & Hindi support</p>
            </div>
            <div className="lcards">
              {[
                {flag:"🇬🇧",title:"English",sub:"Full audit reports",        samp:"Invoice SAL-002: Inter-state supply but CGST+SGST charged"},
                {flag:"🇮🇳",title:"Hindi",  sub:"हिंदी में ऑडिट रिपोर्ट",  samp:"इनवॉइस SAL-002: अंतर-राज्य आपूर्ति में CGST+SGST लगाया"},
                {flag:"🏛️",title:"Marathi",sub:"मराठी मध्ये ऑडिट अहवाल", samp:"बीजक SAL-002: आंतरराज्य पुरवठ्यावर CGST+SGST आकारला"},
              ].map((l,i)=>(
                <div key={l.title} className={`lcard fade-up d${i+1}`}>
                  <div className="flag">{l.flag}</div>
                  <h3>{l.title}</h3>
                  <p>{l.sub}</p>
                  <div className="lsamp">{l.samp}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* TESTIMONIALS */}
        <section className="trust">
          <div className="lc">
            <div className="sl">
              <div className="ol fade-up">Built for CAs</div>
              <h2 className="fade-up d1">Why CAs <span className="gt">Love AuditAI</span></h2>
            </div>
            <div className="tg">
              {[
                {q:"I used to spend 3-4 hours per client matching invoices. AuditAI does it in 2 minutes. The Marathi report feature is amazing for my clients in Pune.",a:"Rajesh Patil, CA",r:"Pune, Maharashtra"},
                {q:"The Notice Predictor warned me about a 78% risk for one client. We fixed 3 issues and it dropped to 15%. Saved my client from a DRC-01 notice.",    a:"Priya Sharma, CA",r:"Mumbai, Maharashtra"},
                {q:"Best part — it works with Tally and Busy exports directly. No manual data entry. My staff loves it. At ₹999/month it's a no-brainer.",              a:"Suresh Kumar, CA",r:"Sangli, Maharashtra"},
              ].map((t,i)=>(
                <div key={t.a} className={`tc fade-up d${i+1}`}>
                  <div className="tq">"{t.q}"</div>
                  <div className="ta">{t.a}</div>
                  <div className="tr">{t.r}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* TEAM */}
        <section className="team" id="team">
          <div className="lc">
            <div className="sl">
              <div className="ol fade-up">The Founders</div>
              <h2 className="fade-up d1">Built by <span className="gt">People Who Care</span></h2>
              <p className="fade-up d2">Two founders on a mission to simplify GST compliance for every CA in India</p>
            </div>
            <div className="team-grid">

              {/* Vivek — Founder */}
              <div className="team-card fade-up d1">
                <div className="team-avatar" style={{background:"var(--grad)"}}>V</div>
                <div className="team-name">Vivek Mane</div>
                <div className="team-role">Founder & CEO</div>
                <div className="team-bio">
                  Building AuditAI to solve the real pain of GST compliance for Indian CAs.
                  Passionate about making complex tax workflows simple, fast, and accurate.
                </div>
                <div className="team-links">
                  <a href="mailto:vivekmane.9731@gmail.com" className="team-link">
                    <span>📧</span> vivekmane.9731@gmail.com
                  </a>
                  <a href="tel:+918208298363" className="team-link">
                    <span>📞</span> +91 82082 98363
                  </a>
                </div>
              </div>

              {/* Vaishu — Co-Founder */}
              <div className="team-card fade-up d2">
                <div className="team-avatar" style={{background:"linear-gradient(135deg,#ec4899,#8b5cf6)"}}>V</div>
                <div className="team-name">Vaishu Powar</div>
                <div className="team-role">Co-Founder</div>
                <div className="team-bio">
                  Co-building AuditAI with a focus on product quality and user experience.
                  Dedicated to making AuditAI the most trusted GST compliance tool in India.
                </div>
                <div className="team-links">
                  <a href="mailto:powarvaishu46@gmail.com" className="team-link">
                    <span>📧</span> powarvaishu46@gmail.com
                  </a>
                </div>
              </div>

            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="cta">
          <div className="lc" style={{position:"relative",zIndex:1}}>
            <h2 className="fade-up">Ready to <span className="gt">Audit Smarter?</span></h2>
            <p className="csub fade-up d1">Join CAs across Maharashtra who are saving 150+ hours/month with AI-powered GST compliance.</p>
            <div className="fade-up d2">
              <a href="/signup" className="btn btn-p" style={{fontSize:18,padding:"18px 48px"}}>Start Your Free Audit →</a>
            </div>
            <p style={{color:"var(--muted)",fontSize:13,marginTop:16}} className="fade-up d3">
              No credit card required · 3 free audits/month · Cancel anytime
            </p>
            <p style={{color:"var(--muted)",fontSize:13,marginTop:10}} className="fade-up d4">
              Questions?{" "}
              <a href="mailto:vivekmane.9731@gmail.com" style={{color:"var(--cyan)",fontWeight:600}}>vivekmane.9731@gmail.com</a>
              {" · "}
              <a href="tel:+918208298363" style={{color:"var(--cyan)",fontWeight:600}}>+91 82082 98363</a>
            </p>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="foot">
          <div className="lc">
            <p style={{fontWeight:600,fontSize:14}}>© 2026 AuditAI · Smart GST Compliance · Made in Maharashtra 🇮🇳</p>

            <div className="foot-links">
              <a href="/privacy">Privacy Policy</a>
              <a href="/terms">Terms of Service</a>
              <a href="#features">Features</a>
              <a href="#pricing">Pricing</a>
              <a href="#team">Team</a>
            </div>

            <div className="foot-founders">
              <div className="founder-item">
                <div className="founder-label">Founder & CEO</div>
                <div className="founder-name">Vivek Mane</div>
                <div className="founder-contacts">
                  <a href="mailto:vivekmane.9731@gmail.com">📧 vivekmane.9731@gmail.com</a>
                  <a href="tel:+918208298363">📞 +91 82082 98363</a>
                </div>
              </div>
              <div style={{width:"1px",background:"var(--border)"}} />
              <div className="founder-item">
                <div className="founder-label">Co-Founder</div>
                <div className="founder-name">Vaishanvi Powar</div>
                <div className="founder-contacts">
                  <a href="mailto:powarvaishu46@gmail.com">📧 powarvaishu46@gmail.com</a>
                </div>
              </div>
            </div>

          </div>
        </footer>

      </div>
    </>
  );
}