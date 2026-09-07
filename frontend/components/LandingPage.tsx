"use client";
import React, { useEffect, useRef, useState } from "react";

export default function LandingPage() {
  const [formData, setFormData] = useState({
    name: "",
    firm: "",
    city: "",
    email: "",
    phone: "",
    clients: "",
    message: "",
  });
  const [status, setStatus] = useState<{ type: "success" | "error" | ""; text: string }>({
    type: "",
    text: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const heroLine1Ref = useRef<HTMLSpanElement>(null);
  const heroLine2Ref = useRef<HTMLElement>(null);
  const heroRef = useRef<HTMLElement>(null);
  const blob1Ref = useRef<HTMLDivElement>(null);
  const blob2Ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 1. Character Slow Reveal Animation
    function textAnimateSlow(el: HTMLElement, startDelay = 0, stagger = 50) {
      const text = el.textContent?.trim() || "";
      el.textContent = "";
      const chars = Array.from(text);

      chars.forEach((ch, i) => {
        const span = document.createElement("span");
        span.className = "hero-char";
        span.textContent = ch === " " ? "\u00A0" : ch;
        span.style.transitionDelay = `${startDelay + i * stagger}ms`;
        el.appendChild(span);
      });

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          el.querySelectorAll(".hero-char").forEach((s) => s.classList.add("char-in"));
        });
      });
      return chars.length;
    }

    if (heroLine1Ref.current && heroLine2Ref.current) {
      const line1Len = textAnimateSlow(heroLine1Ref.current, 200, 50);
      textAnimateSlow(heroLine2Ref.current, 200 + line1Len * 50 + 150, 50);
    }

    // 2. Interactive Mouse Parallax Blobs
    const hero = heroRef.current;
    const blob1 = blob1Ref.current;
    const blob2 = blob2Ref.current;

    let mouseX = 0,
      mouseY = 0,
      targetX = 0,
      targetY = 0,
      ticking = false;

    const handleMouseMove = (e: MouseEvent) => {
      if (!hero) return;
      const rect = hero.getBoundingClientRect();
      targetX = ((e.clientX - rect.left) / rect.width - 0.5) * 40;
      targetY = ((e.clientY - rect.top) / rect.height - 0.5) * 40;
      if (!ticking) {
        ticking = true;
        requestAnimationFrame(updateBlobs);
      }
    };

    const handleMouseLeave = () => {
      targetX = 0;
      targetY = 0;
    };

    function updateBlobs() {
      mouseX += (targetX - mouseX) * 0.08;
      mouseY += (targetY - mouseY) * 0.08;
      if (blob1) blob1.style.transform = `translate(${mouseX}px, ${mouseY}px)`;
      if (blob2) blob2.style.transform = `translate(${-mouseX * 0.8}px, ${-mouseY * 0.8}px)`;

      if (Math.abs(targetX - mouseX) > 0.05 || Math.abs(targetY - mouseY) > 0.05) {
        requestAnimationFrame(updateBlobs);
      } else {
        ticking = false;
      }
    }

    if (hero) {
      hero.addEventListener("mousemove", handleMouseMove);
      hero.addEventListener("mouseleave", handleMouseLeave);
    }

    // 3. Scroll Reveal Observer
    const revealTargets = document.querySelectorAll(".reveal-init");
    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const el = entry.target as HTMLElement;
            const siblings = el.parentElement
              ? Array.from(el.parentElement.children).filter((c) =>
                  c.classList.contains("reveal-init")
                )
              : [];
            if (siblings.length > 1) {
              el.style.transitionDelay = `${(siblings.indexOf(el) % 4) * 0.09}s`;
            }
            el.classList.add("revealed");
            obs.unobserve(el);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" }
    );

    revealTargets.forEach((el) => observer.observe(el));

    return () => {
      if (hero) {
        hero.removeEventListener("mousemove", handleMouseMove);
        hero.removeEventListener("mouseleave", handleMouseLeave);
      }
      observer.disconnect();
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setStatus({ type: "", text: "" });

    try {
      const res = await fetch("/api/v1/enquiry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        setStatus({
          type: "success",
          text: "✓ Request received! We will reach out within 24 hours.",
        });
        setFormData({
          name: "",
          firm: "",
          city: "",
          email: "",
          phone: "",
          clients: "",
          message: "",
        });
      } else {
        throw new Error("Failed");
      }
    } catch {
      const subject = `Early Access Request — ${formData.name}`;
      const body = `Name: ${formData.name}\nFirm: ${formData.firm}\nCity: ${formData.city}\nEmail: ${formData.email}\nPhone: ${formData.phone}\nClients: ${formData.clients}\n\nPain Point:\n${formData.message}`;
      window.location.href = `mailto:hello@auditai.in?subject=${encodeURIComponent(
        subject
      )}&body=${encodeURIComponent(body)}`;
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');
        
        :root{
          --ink:#0a0d14;
          --ink2:#141824;
          --surface:#f8f9fc;
          --card:#ffffff;
          --border:#e4e8f0;
          --border2:#d0d7e8;
          --text:#0a0d14;
          --muted:#5a6882;
          --muted2:#7d889e;
          --accent:#1a56f5;
          --accent2:#0d3fd4;
          --accent-glow:rgba(26,86,245,0.12);
          --teal:#008b73;
          --teal-glow:rgba(0,139,115,0.12);
          --amber:#d97706;
          --red:#dc2626;
          --green:#16a34a;
          --grad:linear-gradient(135deg,#1a56f5 0%,#008b73 100%);
          --grad-subtle:linear-gradient(135deg,rgba(26,86,245,0.08) 0%,rgba(0,139,115,0.08) 100%);
        }

        .landing-body {
          font-family: 'DM Sans', sans-serif;
          background: var(--surface);
          color: var(--text);
          overflow-x: hidden;
          line-height: 1.6;
          -webkit-font-smoothing: antialiased;
          min-height: 100vh;
        }

        .serif{font-family:'Instrument Serif',serif}
        .mono{font-family:'JetBrains Mono',monospace}
        .grad-text{
          background:linear-gradient(135deg,#1a56f5 0%,#008b73 100%);
          -webkit-background-clip:text;
          -webkit-text-fill-color:transparent;
          background-clip:text;
        }

        .container{max-width:1100px;margin:0 auto;padding:0 28px}

        .btn{display:inline-flex;align-items:center;gap:8px;padding:14px 28px;border-radius:10px;font-weight:600;font-size:15px;cursor:pointer;border:none;transition:all .25s;letter-spacing:-.01em;text-decoration:none}
        .btn-primary{background:var(--accent);color:#fff !important;box-shadow:0 4px 24px var(--accent-glow),inset 0 1px 0 rgba(255,255,255,.15)}
        .btn-primary:hover{background:var(--accent2);transform:translateY(-1px);box-shadow:0 8px 32px rgba(26,86,245,.25)}
        .btn-ghost{background:transparent;color:var(--text) !important;border:1.5px solid var(--border2)}
        .btn-ghost:hover{border-color:var(--accent);color:var(--accent) !important;background:var(--accent-glow)}
        .btn-lg{padding:16px 36px;font-size:16px;border-radius:12px}

        @keyframes fadeUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
        @keyframes pulseGlow{0%,100%{opacity:.5}50%{opacity:1}}
        @keyframes barIn{from{width:0}to{width:var(--w)}}
        @keyframes floatY{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}

        .fu{animation:fadeUp .7s cubic-bezier(.22,1,.36,1) both}
        .fu-1{animation-delay:.08s}.fu-2{animation-delay:.16s}.fu-3{animation-delay:.24s}
        .fu-4{animation-delay:.32s}.fu-5{animation-delay:.4s}

        .reveal-init{opacity:0;transform:translateY(28px);transition:opacity .7s cubic-bezier(.22,1,.36,1), transform .7s cubic-bezier(.22,1,.36,1);will-change:opacity,transform}
        .reveal-init.revealed{opacity:1;transform:translateY(0)}

        /* Navbar */
        nav.landing-nav{position:fixed;top:0;width:100%;z-index:1000;padding:0;backdrop-filter:blur(24px) saturate(1.8);background:rgba(248,249,252,.85);border-bottom:1px solid rgba(228,232,240,.7)}
        nav.landing-nav .wrap{display:flex;align-items:center;justify-content:space-between;height:64px}
        .logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:19px;letter-spacing:-.03em}
        .logo-mark{width:36px;height:36px;border-radius:8px;box-shadow:0 2px 8px rgba(26,86,245,.15);flex-shrink:0}
        nav.landing-nav .links{display:flex;align-items:center;gap:10px}
        nav.landing-nav .links a{font-size:14px;font-weight:500;color:var(--muted);padding:7px 14px;border-radius:8px;transition:all .2s}
        nav.landing-nav .links a:hover{color:var(--text);background:rgba(0,0,0,.05)}
        .nav-cta{padding:9px 20px;font-size:13px;font-weight:600;border-radius:8px}

        /* Hero */
        .hero{padding:140px 0 80px;position:relative;overflow:hidden}
        .hero-bg{position:absolute;inset:0;pointer-events:none}
        .hero-bg .blob1{position:absolute;top:-120px;right:-100px;width:600px;height:600px;border-radius:50%;background:radial-gradient(circle,rgba(26,86,245,.08) 0%,transparent 70%);will-change:transform;transition:transform .12s cubic-bezier(.2,.8,.4,1)}
        .hero-bg .blob2{position:absolute;bottom:-80px;left:-80px;width:500px;height:500px;border-radius:50%;background:radial-gradient(circle,rgba(0,139,115,.07) 0%,transparent 70%);will-change:transform;transition:transform .12s cubic-bezier(.2,.8,.4,1)}
        .hero-bg .grid{position:absolute;inset:0;background-image:linear-gradient(rgba(26,86,245,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(26,86,245,.04) 1px,transparent 1px);background-size:60px 60px;mask-image:radial-gradient(ellipse 80% 60% at 50% 0%,black 40%,transparent 100%)}
        .hero-inner{display:grid;grid-template-columns:1fr 420px;gap:64px;align-items:center;position:relative;z-index:1}
        .hero-tag{background:var(--grad-subtle);border:1px solid rgba(26,86,245,.2);color:var(--accent);font-size:12px;font-weight:600;padding:6px 14px;border-radius:100px;display:inline-flex;align-items:center;gap:6px;margin-bottom:24px;letter-spacing:.02em}
        .hero-tag .pulse{width:6px;height:6px;border-radius:50%;background:var(--teal);animation:pulseGlow 1.8s ease-in-out infinite}
        .hero h1{font-size:clamp(40px,4.5vw,58px);font-weight:700;line-height:1.1;letter-spacing:-.04em;margin-bottom:22px}
        .hero h1 em{font-style:normal;font-family:'Instrument Serif',serif;font-weight:400;color:#008b73}
        .hero-char{display:inline;opacity:0;transition:opacity 0.45s ease-out}
        .hero-char.char-in{opacity:1}
        .hero .sub{font-size:17px;color:var(--muted);line-height:1.7;max-width:480px;margin-bottom:36px;font-weight:400}
        .hero-actions{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:32px}
        .early-note{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--muted);font-weight:500}
        .early-note .dot-live{width:7px;height:7px;border-radius:50%;background:var(--teal);animation:pulseGlow 1.8s ease-in-out infinite;flex-shrink:0}

        /* Widget */
        .notice-widget{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:24px;box-shadow:0 24px 64px rgba(10,13,20,.08),0 4px 16px rgba(10,13,20,.04);animation:floatY 5s ease-in-out infinite}
        .nw-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
        .nw-title{font-size:13px;font-weight:600;color:var(--muted)}
        .nw-badge{font-size:10px;font-weight:700;padding:4px 10px;border-radius:6px;letter-spacing:.04em}
        .nw-badge.red{background:#fef2f2;color:var(--red);border:1px solid #fecaca}
        .nw-sample-tag{font-size:11px;color:var(--muted2);margin-bottom:16px;font-style:italic}
        .nw-score{display:flex;align-items:flex-end;gap:8px;margin-bottom:6px}
        .nw-score .num{font-size:52px;font-weight:800;color:var(--red);line-height:1;letter-spacing:-.04em}
        .nw-score .pct{font-size:18px;color:var(--red);font-weight:600;margin-bottom:8px}
        .nw-label{font-size:12px;color:var(--muted);margin-bottom:16px}
        .nw-bar-wrap{height:6px;background:#f1f3f8;border-radius:3px;overflow:hidden;margin-bottom:20px}
        .nw-bar{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--amber),var(--red));width:0;animation:barIn 1.5s cubic-bezier(.22,1,.36,1) .8s forwards;--w:95%}
        .nw-row{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:13px}
        .nw-row:last-child{border:none}
        .nw-row .label{display:flex;align-items:center;gap:8px;color:var(--muted)}
        .nw-row .dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
        .nw-row .val{font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700}
        .nw-whatif{margin-top:16px;background:linear-gradient(135deg,#f0fdf4,#ecfdf5);border:1px solid #bbf7d0;border-radius:12px;padding:14px 16px;display:flex;align-items:center;justify-content:space-between}
        .nw-whatif .label{font-size:12px;color:#166534}
        .nw-whatif .nums{font-size:13px;font-weight:700}
        .nw-whatif .from{color:var(--red);text-decoration:line-through;margin-right:6px}
        .nw-whatif .to{color:var(--green)}

        /* Sections */
        .features{padding:100px 0;background:var(--surface)}
        .section-head{margin-bottom:56px}
        .section-head .eyebrow{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin-bottom:12px}
        .section-head h2{font-size:clamp(28px,3.5vw,42px);font-weight:700;letter-spacing:-.035em;line-height:1.1;margin-bottom:14px;color:var(--text);text-shadow:0 1px 2px rgba(10,13,20,.03)}
        .section-head p{font-size:16px;color:var(--muted);max-width:480px;line-height:1.7}
        .feat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border);border:1px solid var(--border);border-radius:20px;overflow:hidden}
        .feat-card{background:var(--card);padding:32px;transition:all .3s cubic-bezier(.22,1,.36,1)}
        .feat-card:hover{background:linear-gradient(135deg,rgba(26,86,245,.03),rgba(0,139,115,.03));transform:translateY(-3px);box-shadow:0 12px 30px rgba(10,13,20,.06)}
        .feat-card .icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:16px;border:1px solid var(--border)}
        .feat-card h3{font-size:16px;font-weight:700;letter-spacing:-.02em;margin-bottom:8px;color:var(--text)}
        .feat-card p{font-size:14px;color:var(--muted);line-height:1.65}
        .feat-card .tag{display:inline-block;font-size:10px;font-weight:700;padding:3px 8px;border-radius:4px;letter-spacing:.05em;margin-top:12px}
        .tag-unique{background:rgba(26,86,245,.08);color:var(--accent)}
        .tag-new{background:rgba(0,139,115,.12);color:var(--teal)}

        .how{padding:100px 0;background:var(--card);color:var(--text);position:relative;overflow:hidden;border-top:1px solid var(--border)}
        .how::before{content:'';position:absolute;inset:0;background-image:linear-gradient(rgba(26,86,245,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(26,86,245,.035) 1px,transparent 1px);background-size:48px 48px;mask-image:radial-gradient(ellipse 90% 70% at 50% 50%,black 40%,transparent 100%)}
        .how .section-head .eyebrow{color:var(--teal)}
        .how .section-head h2{color:var(--text);text-shadow:0 1px 2px rgba(10,13,20,.03)}
        .how .section-head p{color:var(--muted)}
        .steps-row{display:grid;grid-template-columns:repeat(3,1fr);gap:32px;position:relative;z-index:1}
        .steps-row::before{content:'';position:absolute;top:36px;left:calc(16.67% + 24px);right:calc(16.67% + 24px);height:2px;background:linear-gradient(90deg,rgba(26,86,245,.25),rgba(0,139,115,.25))}
        .step-card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:32px;text-align:center;box-shadow:0 4px 16px rgba(10,13,20,.03);transition:all .3s cubic-bezier(.22,1,.36,1)}
        .step-card:hover{transform:translateY(-4px);box-shadow:0 16px 36px rgba(10,13,20,.07);border-color:var(--border2)}
        .step-card .num{width:56px;height:56px;border-radius:50%;background:var(--grad);display:flex;align-items:center;justify-content:center;font-size:18px;font-weight:800;color:#fff;margin:0 auto 20px;box-shadow:0 6px 24px var(--accent-glow)}
        .step-card h3{font-size:16px;font-weight:700;color:var(--text);margin-bottom:10px;letter-spacing:-.02em}
        .step-card p{font-size:14px;color:var(--muted);line-height:1.65}

        .stats{padding:80px 0;background:var(--surface);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
        .stats-label{text-align:center;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted2);margin-bottom:32px}
        .stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:0;text-align:center}
        .stat-item{padding:32px 24px;border-right:1px solid var(--border)}
        .stat-item:last-child{border:none}
        .stat-num{font-size:42px;font-weight:800;letter-spacing:-.04em;line-height:1;margin-bottom:6px;text-shadow:0 2px 10px rgba(26,86,245,.1)}
        .stat-label{font-size:14px;color:var(--muted)}

        .pricing{padding:100px 0;background:var(--card)}
        .price-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;max-width:960px;margin:0 auto}
        .price-card{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:36px;position:relative;display:flex;flex-direction:column;box-shadow:0 4px 16px rgba(10,13,20,.03);transition:transform .25s,box-shadow .25s,border-color .25s}
        .price-card:hover{transform:translateY(-4px);box-shadow:0 18px 44px rgba(10,13,20,.09);border-color:var(--border2)}
        .price-card.popular{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent),0 16px 48px var(--accent-glow)}
        .price-card .pop-badge{position:absolute;top:-13px;left:50%;transform:translateX(-50%);background:var(--grad);color:#fff;font-size:11px;font-weight:700;padding:4px 16px;border-radius:100px;letter-spacing:.06em;white-space:nowrap}
        .price-card .plan-name{font-size:13px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:16px}
        .price-card .price{font-size:44px;font-weight:800;letter-spacing:-.04em;line-height:1;margin-bottom:4px;color:var(--text)}
        .price-card .period{font-size:13px;color:var(--muted);margin-bottom:28px}
        .price-card .divider{height:1px;background:var(--border);margin-bottom:24px}
        .price-card .feat-list{flex:1;margin-bottom:28px;list-style:none;padding:0}
        .price-card .feat-list li{display:flex;align-items:flex-start;gap:9px;font-size:14px;color:var(--muted);padding:6px 0;line-height:1.4}
        .price-card .feat-list li .ck{color:var(--teal);font-weight:700;margin-top:1px;flex-shrink:0}
        .price-card .feat-list li .no{color:var(--border2);flex-shrink:0}
        .price-card .feat-list li.dim{opacity:.45}
        .price-card .cta-btn{display:flex;align-items:center;justify-content:center;gap:8px;padding:14px;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;transition:all .2s;border:none;text-decoration:none}
        .cta-accent{background:var(--accent);color:#fff !important;box-shadow:0 4px 16px var(--accent-glow)}
        .cta-accent:hover{background:var(--accent2);transform:translateY(-1px);box-shadow:0 8px 24px rgba(26,86,245,.25)}
        .cta-outline{background:transparent;border:1.5px solid var(--border2);color:var(--text) !important}
        .cta-outline:hover{border-color:var(--accent);color:var(--accent) !important;background:var(--accent-glow)}

        .languages{padding:100px 0;background:var(--surface);color:var(--text);position:relative;overflow:hidden;border-top:1px solid var(--border)}
        .languages::before{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:900px;height:900px;border-radius:50%;background:radial-gradient(circle,rgba(0,139,115,.06) 0%,transparent 65%);pointer-events:none}
        .languages .section-head .eyebrow{color:var(--teal)}
        .languages .section-head h2{color:var(--text);text-shadow:0 1px 2px rgba(10,13,20,.03)}
        .languages .section-head p{color:var(--muted)}
        .lang-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;position:relative;z-index:1}
        .lang-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px;box-shadow:0 4px 16px rgba(10,13,20,.03);transition:all .3s cubic-bezier(.22,1,.36,1)}
        .lang-card:hover{background:var(--card);border-color:rgba(0,139,115,.35);transform:translateY(-3px);box-shadow:0 16px 36px rgba(10,13,20,.07)}
        .lang-icon{width:40px;height:40px;border-radius:10px;margin-bottom:16px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(10,13,20,.05)}
        .lang-card h3{font-size:17px;font-weight:700;color:var(--text);margin-bottom:4px;letter-spacing:-.02em}
        .lang-card .sub{font-size:13px;color:var(--muted);margin-bottom:16px}
        .lang-sample{font-size:12px;color:var(--teal);background:rgba(0,139,115,.06);border:1px solid rgba(0,139,115,.15);padding:10px 14px;border-radius:8px;line-height:1.5;font-family:'DM Sans',sans-serif;font-weight:500}

        .enquiry{padding:100px 0;background:var(--card);border-top:1px solid var(--border)}
        .enquiry-wrap{display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:start}
        .enquiry-info .eyebrow{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin-bottom:12px}
        .enquiry-info h2{font-size:clamp(26px,3vw,36px);font-weight:700;letter-spacing:-.03em;line-height:1.15;margin-bottom:16px;color:var(--text)}
        .enquiry-info p{font-size:15px;color:var(--muted);line-height:1.75;margin-bottom:24px}
        .enquiry-perks{display:flex;flex-direction:column;gap:14px}
        .enquiry-perk{display:flex;align-items:flex-start;gap:10px;font-size:14px;color:var(--muted)}
        .enquiry-perk .ck{color:var(--teal);font-weight:700;flex-shrink:0}
        .enquiry-direct{margin-top:28px;padding-top:24px;border-top:1px solid var(--border)}
        .enquiry-direct .label{font-size:12px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--muted2);margin-bottom:10px}
        .enquiry-direct a{display:flex;align-items:center;gap:8px;font-size:14px;color:var(--accent);font-weight:600;margin-bottom:6px;text-decoration:none}

        .enquiry-form{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:32px;box-shadow:0 8px 32px rgba(10,13,20,.05)}
        .form-row{margin-bottom:18px}
        .form-row label{display:block;font-size:13px;font-weight:600;color:var(--text);margin-bottom:7px}
        .form-row input,.form-row select,.form-row textarea{width:100%;padding:12px 14px;border-radius:10px;border:1.5px solid var(--border2);background:var(--card);font-family:'DM Sans',sans-serif;font-size:14px;color:var(--text);transition:border-color .2s;box-sizing:border-box}
        .form-row input:focus,.form-row select:focus,.form-row textarea:focus{outline:none;border-color:var(--accent)}
        .form-row textarea{resize:vertical;min-height:90px}
        .form-2col{display:grid;grid-template-columns:1fr 1fr;gap:14px}
        .form-submit{width:100%;padding:14px;border-radius:10px;font-weight:700;font-size:15px;border:none;cursor:pointer;background:var(--accent);color:#fff;box-shadow:0 4px 16px var(--accent-glow);transition:all .2s;margin-top:6px}
        .form-submit:hover{background:var(--accent2);transform:translateY(-1px)}
        .form-submit:disabled{opacity:0.6;cursor:not-allowed}
        .form-status{font-size:13px;margin-top:12px;text-align:center;font-weight:600}
        .form-status.success{color:var(--green)}
        .form-status.error{color:var(--red)}
        .form-note{font-size:12px;color:var(--muted2);margin-top:12px;text-align:center}

        .cta-banner{padding:100px 0;background:var(--card);position:relative;overflow:hidden;border-top:1px solid var(--border)}
        .cta-banner::before{content:'';position:absolute;bottom:-100px;right:-100px;width:600px;height:600px;background:radial-gradient(circle,rgba(26,86,245,.08) 0%,transparent 65%);pointer-events:none}
        .cta-banner::after{content:'';position:absolute;top:-80px;left:-80px;width:500px;height:500px;background:radial-gradient(circle,rgba(0,139,115,.06) 0%,transparent 65%);pointer-events:none}
        .cta-banner .inner{text-align:center;position:relative;z-index:1}
        .cta-banner h2{font-size:clamp(32px,4vw,52px);font-weight:700;color:var(--text);letter-spacing:-.04em;line-height:1.1;margin-bottom:16px;text-shadow:0 1px 2px rgba(10,13,20,.03)}
        .cta-banner p{font-size:17px;color:var(--muted);max-width:480px;margin:0 auto 36px;line-height:1.7}
        .cta-banner .fine{font-size:13px;color:var(--muted2);margin-top:16px}

        footer.landing-foot{background:var(--surface);border-top:1px solid var(--border);padding:48px 0}
        footer.landing-foot .foot-inner{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:20px}
        footer.landing-foot .logo{color:var(--text)}
        footer.landing-foot .links{display:flex;gap:24px}
        footer.landing-foot .links a{font-size:13px;color:var(--muted);transition:color .2s;text-decoration:none}
        footer.landing-foot .links a:hover{color:var(--text)}
        footer.landing-foot .copy{font-size:12px;color:var(--muted2);width:100%;text-align:center;padding-top:24px;border-top:1px solid var(--border);margin-top:20px}

        @media(max-width:900px){
          .hero-inner{grid-template-columns:1fr}
          .notice-widget{max-width:440px;margin:40px auto 0}
          .feat-grid{grid-template-columns:1fr 1fr}
          .steps-row::before{display:none}
          .stats-grid{grid-template-columns:repeat(2,1fr)}
          .stat-item:nth-child(2){border-right:none}
          .stat-item:nth-child(3){border-top:1px solid var(--border)}
          .price-grid,.lang-grid{grid-template-columns:1fr}
          .steps-row{grid-template-columns:1fr}
          .enquiry-wrap{grid-template-columns:1fr;gap:36px}
        }
        @media(max-width:600px){
          nav.landing-nav .links a:not(.nav-cta){display:none}
          .feat-grid{grid-template-columns:1fr}
          .stats-grid{grid-template-columns:1fr 1fr}
          .hero h1{font-size:36px}
          .form-2col{grid-template-columns:1fr}
        }
      `}</style>

      <div className="landing-body">
        {/* NAVBAR */}
        <nav className="landing-nav">
          <div className="container wrap">
            <a href="#" className="logo">
              <svg className="logo-mark" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
                <rect width="36" height="36" rx="8" fill="url(#navgrad)" />
                <path
                  d="M11 24V14l7-4 7 4v10"
                  stroke="#fff"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
                <path
                  d="M14 20l3-3 2 2 4-4"
                  stroke="#fff"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
                <defs>
                  <linearGradient id="navgrad" x1="0" y1="0" x2="36" y2="36">
                    <stop offset="0" stopColor="#1a56f5" />
                    <stop offset="1" stopColor="#008b73" />
                  </linearGradient>
                </defs>
              </svg>
              <span>
                Audit<span className="grad-text">AI</span>
              </span>
            </a>
            <div className="links">
              <a href="#features">Features</a>
              <a href="#how">How it Works</a>
              <a href="#pricing">Pricing</a>
              <a href="/upload" className="btn btn-ghost nav-cta" style={{ marginRight: 6 }}>
                Live Demo
              </a>
              <a href="#enquiry" className="btn btn-primary nav-cta">
                Get Early Access →
              </a>
            </div>
          </div>
        </nav>

        {/* HERO */}
        <section className="hero" ref={heroRef}>
          <div className="hero-bg">
            <div className="blob1" ref={blob1Ref}></div>
            <div className="blob2" ref={blob2Ref}></div>
            <div className="grid"></div>
          </div>
          <div className="container">
            <div className="hero-inner">
              <div>
                <div className="hero-tag fu">
                  <span className="pulse"></span>
                  India's First AI-Powered GST Notice Predictor
                </div>
                <h1>
                  <span ref={heroLine1Ref}>Stop GST Notices</span>
                  <br />
                  <em ref={heroLine2Ref}>Before They Arrive</em>
                </h1>
                <p className="sub fu" style={{ animationDelay: "2.0s" }}>
                  Upload your Excel files. Our AI runs 10+ checks in minutes — detects mismatches,
                  predicts notice risk, and gives fix-it reports in Hindi, English & Marathi.
                </p>
                <div className="hero-actions fu" style={{ animationDelay: "2.2s" }}>
                  <a href="#enquiry" className="btn btn-primary btn-lg">
                    Get Early Access
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path
                        d="M3 8h10M9 4l4 4-4 4"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </a>
                  <a href="#how" className="btn btn-ghost btn-lg">
                    See How It Works
                  </a>
                </div>
                <div className="early-note fu" style={{ animationDelay: "2.4s" }}>
                  <span className="dot-live"></span>
                  Currently onboarding early Chartered Accountant partners in Maharashtra
                </div>
              </div>

              <div className="notice-widget fu fu-5">
                <div className="nw-header">
                  <span className="nw-title">GST Notice Probability</span>
                  <span className="nw-badge red">VERY HIGH RISK</span>
                </div>
                <div className="nw-sample-tag">Illustrative sample report</div>
                <div className="nw-score">
                  <span className="num">95</span>
                  <span className="pct">%</span>
                </div>
                <div className="nw-label">Notice likely within 30 days</div>
                <div className="nw-bar-wrap">
                  <div className="nw-bar"></div>
                </div>

                <div>
                  <div className="nw-row">
                    <span className="label">
                      <span className="dot" style={{ background: "#e53e3e" }}></span>Tax
                      Computation Error
                    </span>
                    <span className="val" style={{ color: "#e53e3e" }}>
                      54%
                    </span>
                  </div>
                  <div className="nw-row">
                    <span className="label">
                      <span className="dot" style={{ background: "#f59e0b" }}></span>ITC Mismatch
                      (2B)
                    </span>
                    <span className="val" style={{ color: "#f59e0b" }}>
                      25%
                    </span>
                  </div>
                  <div className="nw-row">
                    <span className="label">
                      <span className="dot" style={{ background: "#1a56f5" }}></span>Filing
                      Non-Compliance
                    </span>
                    <span className="val" style={{ color: "#1a56f5" }}>
                      10%
                    </span>
                  </div>
                </div>

                <div className="nw-whatif">
                  <span className="label">✦ If you fix all issues</span>
                  <span className="nums">
                    <span className="from">95%</span>
                    <span className="to">→ 18%</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section className="features" id="features">
          <div className="container">
            <div className="section-head reveal-init">
              <div className="eyebrow">Powerful Features</div>
              <h2>
                Everything a CA Needs,
                <br />
                <span className="grad-text">Built Into One Tool</span>
              </h2>
              <p>
                Covers manufacturing, trading/retail, services, IT/SaaS, healthcare, construction,
                hospitality, and export/import sectors.
              </p>
            </div>
            <div className="feat-grid">
              <div className="feat-card reveal-init">
                <div className="icon" style={{ background: "#fef2f2", borderColor: "#fecaca" }}>
                  🔮
                </div>
                <h3>GST Notice Predictor</h3>
                <p>
                  Predicts ASMT-10, DRC-01, ADT-01 notice probability. Shows exact risk areas and
                  what-if analysis — fix issues and watch probability drop.
                </p>
                <span className="tag tag-unique">CORE DIFFERENTIATOR</span>
              </div>
              <div className="feat-card reveal-init">
                <div className="icon" style={{ background: "#eff6ff", borderColor: "#bfdbfe" }}>
                  🔍
                </div>
                <h3>10+ Smart Audit Checks</h3>
                <p>
                  Tax type mismatch, GSTIN validation, GSTR-1/2B reconciliation, duplicate
                  invoices, sector-specific rules — all automated.
                </p>
              </div>
              <div className="feat-card reveal-init">
                <div className="icon" style={{ background: "#f0fdfa", borderColor: "#99f6e4" }}>
                  🌐
                </div>
                <h3>Hindi & Marathi Reports</h3>
                <p>
                  Issue descriptions, fix steps, and legal references generated in your client's
                  preferred language.
                </p>
                <span className="tag tag-new">MULTILINGUAL</span>
              </div>
              <div className="feat-card reveal-init">
                <div className="icon" style={{ background: "#fff7ed", borderColor: "#fed7aa" }}>
                  📊
                </div>
                <h3>Risk Score Dashboard</h3>
                <p>
                  Every client gets a compliance score (0–100) with severity breakdown, trend
                  tracking, and alert summaries in one screen.
                </p>
              </div>
              <div className="feat-card reveal-init">
                <div className="icon" style={{ background: "#fdf4ff", borderColor: "#e9d5ff" }}>
                  📋
                </div>
                <h3>Professional PDF Reports</h3>
                <p>
                  Audit reports with compliance score, ITC at risk, legal references (Section 16,
                  25, 37, 47), and step-by-step fix instructions.
                </p>
              </div>
              <div className="feat-card reveal-init">
                <div className="icon" style={{ background: "#f0fdf4", borderColor: "#bbf7d0" }}>
                  🏢
                </div>
                <h3>Sector-Specific Checks</h3>
                <p>
                  Healthcare, Manufacturing, Retail, IT Services, Real Estate, Restaurant,
                  Export/Import — each with its own GST rule set.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section className="how" id="how">
          <div className="container">
            <div className="section-head reveal-init" style={{ maxWidth: 520 }}>
              <div className="eyebrow">Simple Process</div>
              <h2>
                From Upload to Audit
                <br />
                in{" "}
                <em
                  style={{
                    fontFamily: "Instrument Serif, serif",
                    fontStyle: "normal",
                    color: "#008b73",
                  }}
                >
                  3 Easy Steps
                </em>
              </h2>
              <p>No training required. No manual data entry. Just upload and get results.</p>
            </div>
            <div className="steps-row">
              <div className="step-card reveal-init">
                <div className="num">1</div>
                <h3>Upload Your Files</h3>
                <p>
                  Upload Sales Register + Purchase Register. Works with Tally, Busy, Zoho, Marg
                  ERP, or any Excel export. Also supports images and PDFs via OCR.
                </p>
              </div>
              <div className="step-card reveal-init">
                <div className="num">2</div>
                <h3>AI Runs 10+ Checks</h3>
                <p>
                  Our engine validates GSTINs, checks tax types, reconciles GSTR-2B, detects
                  duplicates, and runs sector-specific rules.
                </p>
              </div>
              <div className="step-card reveal-init">
                <div className="num">3</div>
                <h3>Get Report + Fix Steps</h3>
                <p>
                  Download a professional PDF with compliance score, notice probability, fix-it
                  steps, and legal references — in English, Hindi, or Marathi.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* PRODUCT FACTS */}
        <div className="stats">
          <div className="container">
            <div className="stats-label reveal-init">What's built so far</div>
            <div className="stats-grid">
              <div className="stat-item reveal-init">
                <div className="stat-num grad-text">10+</div>
                <div className="stat-label">Automated audit checks</div>
              </div>
              <div className="stat-item reveal-init">
                <div className="stat-num grad-text">8</div>
                <div className="stat-label">Sector-specific rule sets</div>
              </div>
              <div className="stat-item reveal-init">
                <div className="stat-num grad-text">200+</div>
                <div className="stat-label">GST compliance rules</div>
              </div>
              <div className="stat-item reveal-init">
                <div className="stat-num grad-text">3</div>
                <div className="stat-label">Languages supported</div>
              </div>
            </div>
          </div>
        </div>

        {/* PRICING */}
        <section className="pricing" id="pricing">
          <div className="container">
            <div className="section-head reveal-init" style={{ textAlign: "center", maxWidth: "none" }}>
              <div className="eyebrow" style={{ textAlign: "center" }}>
                Simple Pricing
              </div>
              <h2 style={{ textAlign: "center" }}>
                Plans That <span className="grad-text">Fit Your Practice</span>
              </h2>
              <p style={{ textAlign: "center", margin: "0 auto" }}>
                Start free. Upgrade when you need more audits, languages, or team access.
              </p>
            </div>
            <div className="price-grid">
              <div className="price-card reveal-init">
                <div className="plan-name">Starter</div>
                <div className="price">₹0</div>
                <div className="period">forever free</div>
                <div className="divider"></div>
                <ul className="feat-list">
                  <li>
                    <span className="ck">✓</span>3 audits / month
                  </li>
                  <li>
                    <span className="ck">✓</span>All 10+ audit checks
                  </li>
                  <li>
                    <span className="ck">✓</span>Notice probability
                  </li>
                  <li>
                    <span className="ck">✓</span>PDF report download
                  </li>
                  <li>
                    <span className="ck">✓</span>English language
                  </li>
                  <li className="dim">
                    <span className="no">✕</span>Unlimited audits
                  </li>
                  <li className="dim">
                    <span className="no">✕</span>Hindi / Marathi reports
                  </li>
                </ul>
                <a href="#enquiry" className="cta-btn cta-outline">
                  Get Started Free
                </a>
              </div>

              <div className="price-card popular reveal-init">
                <div className="pop-badge">⚡ MOST POPULAR</div>
                <div className="plan-name">Pro</div>
                <div className="price grad-text">₹999</div>
                <div className="period">per month · billed monthly</div>
                <div className="divider"></div>
                <ul className="feat-list">
                  <li>
                    <span className="ck">✓</span>Unlimited audits
                  </li>
                  <li>
                    <span className="ck">✓</span>All 10+ audit checks
                  </li>
                  <li>
                    <span className="ck">✓</span>Notice predictor + What-if
                  </li>
                  <li>
                    <span className="ck">✓</span>Hindi + Marathi reports
                  </li>
                  <li>
                    <span className="ck">✓</span>OCR scanning (images/PDFs)
                  </li>
                  <li>
                    <span className="ck">✓</span>GSTR-2B reconciliation
                  </li>
                  <li>
                    <span className="ck">✓</span>Priority email support
                  </li>
                </ul>
                <a href="#enquiry" className="cta-btn cta-accent">
                  Get Early Access →
                </a>
              </div>

              <div className="price-card reveal-init">
                <div className="plan-name">Firm</div>
                <div className="price">₹2,499</div>
                <div className="period">per month · up to 5 users</div>
                <div className="divider"></div>
                <ul className="feat-list">
                  <li>
                    <span className="ck">✓</span>Everything in Pro
                  </li>
                  <li>
                    <span className="ck">✓</span>5 team members
                  </li>
                  <li>
                    <span className="ck">✓</span>Bulk audit (50+ clients)
                  </li>
                  <li>
                    <span className="ck">✓</span>Supplier trust scores
                  </li>
                  <li>
                    <span className="ck">✓</span>White-label PDF reports
                  </li>
                  <li>
                    <span className="ck">✓</span>API access
                  </li>
                  <li>
                    <span className="ck">✓</span>Dedicated account manager
                  </li>
                </ul>
                <a href="#enquiry" className="cta-btn cta-outline">
                  Contact Sales
                </a>
              </div>
            </div>
            <p style={{ textAlign: "center", fontSize: 13, color: "var(--muted2)", marginTop: 24 }}>
              🔒 Payments via Razorpay (coming with launch) &nbsp;·&nbsp; Cancel anytime
              &nbsp;·&nbsp; GST invoice provided
            </p>
          </div>
        </section>

        {/* LANGUAGES */}
        <section className="languages" id="languages">
          <div className="container">
            <div className="section-head reveal-init" style={{ maxWidth: 480 }}>
              <div className="eyebrow">Multi-Language Support</div>
              <h2>
                Reports in
                <br />
                <em
                  style={{
                    fontFamily: "Instrument Serif, serif",
                    fontStyle: "normal",
                    color: "var(--teal)",
                  }}
                >
                  Your Language
                </em>
              </h2>
              <p>
                GST audit reports with proper Marathi & Hindi support — issue descriptions, fix
                steps, and legal references all translated.
              </p>
            </div>
            <div className="lang-grid">
              <div className="lang-card reveal-init">
                <div className="lang-icon" style={{ background: "#eff6ff" }}>
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#1a56f5"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="2" y1="12" x2="22" y2="12"></line>
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                  </svg>
                </div>
                <h3>English</h3>
                <div className="sub">Full audit reports in English</div>
                <div className="lang-sample">
                  "Invoice SAL-002: Inter-state supply but CGST+SGST charged. Fix: Change to IGST @
                  18%."
                </div>
              </div>
              <div className="lang-card reveal-init">
                <div className="lang-icon" style={{ background: "#fff7ed" }}>
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                  </svg>
                </div>
                <h3>हिंदी</h3>
                <div className="sub">हिंदी में सम्पूर्ण ऑडिट रिपोर्ट</div>
                <div className="lang-sample">
                  "इनवॉइस SAL-002: अंतर-राज्य आपूर्ति पर CGST+SGST लगाया गया है। सुधार: IGST @ 18% लागू
                  करें।"
                </div>
              </div>
              <div className="lang-card reveal-init">
                <div className="lang-icon" style={{ background: "#f0fdf4" }}>
                  <svg
                    width="24"
                    height="24"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="#16a34a"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M3 21h18M3 7v1a3 3 0 0 0 6 0V7m0 1a3 3 0 0 0 6 0V7m0 1a3 3 0 0 0 6 0V7H3l2-4h14l2 4M5 21V10.85M19 21V10.85M9 21v-4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v4"></path>
                  </svg>
                </div>
                <h3>मराठी</h3>
                <div className="sub">मराठीत संपूर्ण ऑडिट अहवाल</div>
                <div className="lang-sample">
                  "बीजक SAL-002: आंतरराज्य पुरवठ्यावर CGST+SGST आकारला. दुरुस्ती: IGST @ 18% लागू करा."
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ENQUIRY */}
        <section className="enquiry" id="enquiry">
          <div className="container">
            <div className="enquiry-wrap">
              <div className="enquiry-info reveal-init">
                <div className="eyebrow">Get Early Access</div>
                <h2>
                  Be Among the First CAs
                  <br />
                  to Use AuditAI
                </h2>
                <p>
                  We're onboarding a small group of Chartered Accountants in Maharashtra to try
                  AuditAI on real client files and shape the product. No cost during early access —
                  just your honest feedback.
                </p>
                <div className="enquiry-perks">
                  <div className="enquiry-perk">
                    <span className="ck">✓</span>Free access during the early access period
                  </div>
                  <div className="enquiry-perk">
                    <span className="ck">✓</span>Direct line to the founders for feedback and
                    requests
                  </div>
                  <div className="enquiry-perk">
                    <span className="ck">✓</span>Your data stays confidential — used only for your
                    own audits
                  </div>
                </div>
                <div className="enquiry-direct">
                  <div className="label">Or reach out directly</div>
                  <a href="mailto:vivekmane.9731@gmail.com">📧 vivekmane.9731@gmail.com</a>
                  <a href="tel:+918208298363">📞 +91 82082 98363</a>
                </div>
              </div>

              <form className="enquiry-form reveal-init" onSubmit={handleSubmit}>
                <div className="form-row">
                  <label htmlFor="ef-name">Full Name *</label>
                  <input
                    type="text"
                    id="ef-name"
                    required
                    placeholder="Your name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
                <div className="form-2col">
                  <div className="form-row">
                    <label htmlFor="ef-firm">Firm Name</label>
                    <input
                      type="text"
                      id="ef-firm"
                      placeholder="CA firm / practice name"
                      value={formData.firm}
                      onChange={(e) => setFormData({ ...formData, firm: e.target.value })}
                    />
                  </div>
                  <div className="form-row">
                    <label htmlFor="ef-city">City</label>
                    <input
                      type="text"
                      id="ef-city"
                      placeholder="e.g. Pune"
                      value={formData.city}
                      onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    />
                  </div>
                </div>
                <div className="form-2col">
                  <div className="form-row">
                    <label htmlFor="ef-email">Email *</label>
                    <input
                      type="email"
                      id="ef-email"
                      required
                      placeholder="you@example.com"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    />
                  </div>
                  <div className="form-row">
                    <label htmlFor="ef-phone">Phone</label>
                    <input
                      type="tel"
                      id="ef-phone"
                      placeholder="+91 XXXXX XXXXX"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    />
                  </div>
                </div>
                <div className="form-row">
                  <label htmlFor="ef-clients">Approx. number of clients you handle</label>
                  <select
                    id="ef-clients"
                    value={formData.clients}
                    onChange={(e) => setFormData({ ...formData, clients: e.target.value })}
                  >
                    <option value="">Select</option>
                    <option value="1-10">1–10</option>
                    <option value="11-50">11–50</option>
                    <option value="51-100">51–100</option>
                    <option value="100+">100+</option>
                  </select>
                </div>
                <div className="form-row">
                  <label htmlFor="ef-message">What's your biggest GST compliance pain point?</label>
                  <textarea
                    id="ef-message"
                    placeholder="e.g. ITC reconciliation takes too long, or clients keep getting notices we didn't see coming..."
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                  ></textarea>
                </div>
                <button type="submit" className="form-submit" disabled={submitting}>
                  {submitting ? "Submitting..." : "Request Early Access"}
                </button>
                {status.text && (
                  <p className={`form-status ${status.type}`}>{status.text}</p>
                )}
                <p className="form-note">We reply personally, usually within 24 hours.</p>
              </form>
            </div>
          </div>
        </section>

        {/* CTA BANNER */}
        <section className="cta-banner">
          <div className="container">
            <div className="inner reveal-init">
              <h2>
                Ready to Audit
                <br />
                <em
                  className="grad-text"
                  style={{ fontFamily: "Instrument Serif, serif", fontStyle: "normal" }}
                >
                  Smarter?
                </em>
              </h2>
              <p>
                Join the early group of CAs shaping AuditAI. No cost, no credit card — just your
                feedback.
              </p>
              <div>
                <a
                  href="#enquiry"
                  className="btn btn-primary btn-lg"
                  style={{ fontSize: 17, padding: "18px 48px" }}
                >
                  Get Early Access
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path
                      d="M3 8h10M9 4l4 4-4 4"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </a>
              </div>
              <p className="fine">
                No credit card required &nbsp;·&nbsp; Free during early access &nbsp;·&nbsp; Cancel
                anytime
              </p>
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="landing-foot">
          <div className="container">
            <div className="foot-inner">
              <div className="logo">
                <svg className="logo-mark" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
                  <rect width="36" height="36" rx="8" fill="url(#footgrad)" />
                  <path
                    d="M11 24V14l7-4 7 4v10"
                    stroke="#fff"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                  <path
                    d="M14 20l3-3 2 2 4-4"
                    stroke="#fff"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                  <defs>
                    <linearGradient id="footgrad" x1="0" y1="0" x2="36" y2="36">
                      <stop offset="0" stopColor="#1a56f5" />
                      <stop offset="1" stopColor="#008b73" />
                    </linearGradient>
                  </defs>
                </svg>
                <span>
                  Audit<span className="grad-text">AI</span>
                </span>
              </div>
              <div className="links">
                <a href="#">Privacy Policy</a>
                <a href="#">Terms of Service</a>
                <a href="mailto:vivekmane.9731@gmail.com">vivekmane.9731@gmail.com</a>
              </div>
            </div>

            <div className="copy">
              © 2026 AuditAI · Smart GST Compliance · Made with ❤️ in Maharashtra, India
            </div>
          </div>
        </footer>
      </div>
    </>
  );
}