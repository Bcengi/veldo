"""VELDO-0246 pilot design screens: writes the four static HTML screens from one geometry.

Run: python3 gen.py && sh render.sh   (from this folder). Static mockups only; no app code.
Every card, edge and label is placed from GEOMETRY below, so a transition always meets its cards.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Section: icons (stroke, 24 grid)
P = {
    'pen': '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    'image': '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
    'eye': '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    'lock': '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    'cal': '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    'send': '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    'file': '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/>',
    'rocket': '<path d="M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2.1-.1-2.9a2.2 2.2 0 0 0-2.9-.1Z"/><path d="m12 15-3-3a22 22 0 0 1 2-4A12.9 12.9 0 0 1 22 2c0 2.7-.8 7.5-6 11a22.4 22.4 0 0 1-4 2Z"/>',
    'box': '<path d="M21 8 12 3 3 8v8l9 5 9-5Z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'minus': '<path d="M5 12h14"/>',
    'fit': '<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/>',
    'undo': '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    'redo': '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>',
    'panel': '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/>',
    'chev': '<path d="m6 9 6 6 6-6"/>',
    'back': '<path d="m15 18-6-6 6-6"/>',
    'term': '<path d="m4 17 6-6-6-6M12 19h8"/>',
    'x': '<path d="M18 6 6 18M6 6l12 12"/>',
    'alert': '<circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>',
    'search': '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    'check': '<path d="M20 6 9 17l-5-5"/>',
    'coin': '<circle cx="12" cy="12" r="9"/><path d="M14.5 9.5c-.4-.9-1.4-1.5-2.5-1.5-1.5 0-2.5.8-2.5 2s1 1.6 2.5 2 2.5.8 2.5 2-1 2-2.5 2c-1.1 0-2.1-.6-2.5-1.5M12 6.5v1.5M12 16v1.5"/>',
    'grid': '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    'inbox': '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1Z"/>',
    'flow': '<circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><path d="M6 9v3a3 3 0 0 0 3 3h6"/>',
    'list': '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    'gear': '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
    'users': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
    'chart': '<path d="M3 3v18h18"/><path d="M7 16v-3M12 16V8M17 16v-6"/>',
    'more': '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    'link': '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
    'kbd': '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
    'trash': '<path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>',
    'copy': '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    'split': '<path d="M12 3.5 20.5 12 12 20.5 3.5 12Z"/><path d="M12 9.5v.01M12 14.5v.01"/>',
    'merge': '<path d="M6 3v3a6 6 0 0 0 6 6"/><path d="M18 3v3a6 6 0 0 1-6 6"/><path d="M12 12v9"/>',
    'clock': '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
}


def ic(name, size=18, cls='i'):
    return ('<svg class="%s" width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>'
            % (cls, size, size, P[name]))


# Section: styles
CSS = r"""
@font-face{font-family:'Plex';src:url(fonts/ibm-plex-sans-latin-wght-normal.woff2) format('woff2');font-weight:100 700}
@font-face{font-family:'PlexMono';src:url(fonts/ibm-plex-mono-latin-400-normal.woff2) format('woff2');font-weight:400}
@font-face{font-family:'PlexMono';src:url(fonts/ibm-plex-mono-latin-500-normal.woff2) format('woff2');font-weight:500}
:root{
 --ink:#171717;--ink-muted:#636363;--paper:#fff;--sunken:#fafafa;--rule:#e5e5e5;--rule-strong:#8f8f8f;
 --wash:#f2f2f2;--amber:#f2a900;--amber-text:#8a5a00;--amber-wash:#fdf3dc;--live:#23a15c;--live-text:#1d7a47;
 --live-wash:#e1f5e9;--stop:#d63b2a;--stop-text:#b42b1c;--stop-wash:#fbe6e2;
 /* VELDO-0246: the flow's own blue (Telegram 37382: Veldo is built on blue). It marks connections, selection,
    drop targets and the path a run took; never a button and never a state. 6.0:1 on white. */
 --flow:#2e5bda;--flow-soft:#9bb2ee;--flow-wash:#edf2fd;--flow-zone:#f5f8fe;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{font-family:'Plex',system-ui,sans-serif;color:var(--ink);background:var(--paper);font-size:16px;
 -webkit-font-smoothing:antialiased;font-feature-settings:'kern'}
body{width:1440px;height:900px;overflow:hidden;position:relative}
body.phone{width:390px;height:844px}
.i{display:block;flex:none}
.mono{font-family:'PlexMono',ui-monospace,monospace}
.num{font-variant-numeric:tabular-nums}

/* shell */
.rail{position:absolute;left:0;top:0;bottom:0;width:52px;border-right:1px solid var(--rule);display:flex;
 flex-direction:column;align-items:center;padding-top:14px;gap:4px;background:var(--paper)}
.rail .dot{width:10px;height:10px;border-radius:50%;background:var(--ink);margin:6px 0 16px}
.rail .r{width:36px;height:36px;border-radius:6px;display:grid;place-items:center;color:var(--ink-muted);position:relative}
.rail .r.on{background:var(--wash);color:var(--ink)}
.rail .sep{width:28px;height:1px;background:var(--rule);margin:8px 0}
.rail .badge{position:absolute;top:2px;right:0;min-width:16px;height:16px;border-radius:8px;background:var(--amber);
 color:var(--ink);font-size:11px;font-weight:650;display:grid;place-items:center;padding:0 4px}
.rail .av{margin-top:auto;margin-bottom:14px;width:30px;height:30px;border-radius:50%;background:var(--wash);
 font-size:12px;font-weight:600;display:grid;place-items:center;color:var(--ink-muted)}

.top{position:absolute;left:52px;right:0;top:0;height:56px;border-bottom:1px solid var(--rule);display:flex;
 align-items:center;padding:0 16px 0 14px;gap:12px;background:var(--paper)}
.ibtn{width:34px;height:34px;border-radius:6px;display:grid;place-items:center;color:var(--ink);border:1px solid transparent}
.ibtn.b{border-color:var(--rule)}
.ibtn.dis{color:#b5b5b5}
.crumb{display:flex;align-items:center;gap:8px;font-size:15px;color:var(--ink-muted)}
.crumb .slash{color:#c4c4c4}
.wf{display:flex;align-items:center;gap:6px;font-size:18px;font-weight:650;letter-spacing:-.015em;color:var(--ink);
 padding:4px 8px;margin-left:-8px;border-radius:6px}
.ver{font-size:14px;color:var(--ink-muted);display:flex;align-items:center;gap:8px}
.ver b{font-weight:600;color:var(--ink)}
.ver .edited{display:inline-flex;align-items:center;gap:6px;color:var(--ink)}
.ver .edited:before{content:'';width:7px;height:7px;border-radius:50%;background:var(--flow)}
.grow{flex:1}
.seg{display:flex;border:1px solid var(--rule);border-radius:8px;padding:3px;gap:2px}
.seg span{font-size:14px;font-weight:600;padding:5px 14px;border-radius:6px;color:var(--ink-muted);display:flex;gap:6px;align-items:center}
.seg span.on{background:var(--ink);color:#fff}
.seg .n{font-weight:500;opacity:.75}
.btn{height:36px;border-radius:6px;border:1px solid var(--rule-strong);padding:0 14px;font-size:14px;font-weight:600;
 display:inline-flex;align-items:center;gap:8px;background:var(--paper);color:var(--ink);white-space:nowrap}
.btn.q{border-color:var(--rule)}
.btn.p{background:var(--ink);border-color:var(--ink);color:#fff}
.btn.lg{height:44px;font-size:15px;padding:0 18px}
.kbd{font-family:'PlexMono',monospace;font-size:12px;border:1px solid var(--rule);border-bottom-width:2px;border-radius:4px;
 padding:0 5px;color:var(--ink-muted);background:var(--paper);line-height:18px}

/* left column: palette or runs */
.left{position:absolute;left:52px;top:56px;bottom:0;width:248px;border-right:1px solid var(--rule);background:var(--paper);
 display:flex;flex-direction:column}
.left h2{font-size:16px;font-weight:650;letter-spacing:-.01em;padding:18px 18px 4px}
.left .sub{font-size:13px;color:var(--ink-muted);padding:0 18px 12px;line-height:1.4}
.search{margin:0 14px 6px;height:36px;border:1px solid var(--rule);border-radius:6px;display:flex;align-items:center;gap:8px;
 padding:0 10px;color:var(--ink-muted);font-size:14px}
.grp{font-size:13px;font-weight:600;color:var(--ink-muted);padding:11px 18px 3px}
.pi{display:flex;gap:10px;align-items:flex-start;padding:6px 10px;margin:0 8px;border-radius:6px}
.pi .pic{width:30px;height:30px;border-radius:6px;border:1px solid var(--rule);display:grid;place-items:center;color:var(--ink);flex:none;background:var(--paper)}
.pi .pt{font-size:14px;font-weight:600;line-height:1.25}
.pi .pd{font-size:13px;color:var(--ink-muted);line-height:1.3;margin-top:1px}
.pi.gate .pic{background:var(--ink);color:#fff;border-color:var(--ink)}
.pi.hov{background:var(--wash)}
.flowrow{display:flex;align-items:center;gap:8px;padding:8px 14px 0 18px}
.flowrow .fl{font-size:13px;font-weight:600;color:var(--ink-muted);width:40px}
.flowrow .ft{flex:1;display:flex;align-items:center;gap:8px;height:34px;border:1px solid var(--rule);border-radius:6px;padding:0 8px 0 4px;font-size:14px;font-weight:600}
.flowrow .ft .pic{width:26px;height:26px;border-radius:5px;display:grid;place-items:center;color:var(--ink)}
.left .foot{margin-top:auto;border-top:1px solid var(--rule);padding:12px 18px;font-size:13px;color:var(--ink-muted);line-height:1.45}

/* canvas */
.canvas{position:absolute;top:56px;bottom:0;overflow:hidden;background-color:var(--sunken);
 background-image:radial-gradient(circle,#dcdcdc 1px,transparent 1.2px);background-size:20px 20px}
.zone{position:absolute;left:0;right:0;bottom:0;background-color:var(--flow-zone);
 background-image:radial-gradient(circle,#d3dcf3 1px,transparent 1.2px);background-size:20px 20px;border-top:1.5px solid var(--ink)}
.zone .zl{position:absolute;left:16px;top:10px;display:flex;gap:8px;align-items:flex-start;font-size:13px;line-height:1.35;color:var(--ink);width:140px;font-weight:500}
svg.edges{position:absolute;left:0;top:0;overflow:visible}
.elab{position:absolute;font-size:13px;color:var(--ink-muted);background:var(--sunken);padding:1px 6px;border-radius:4px;white-space:nowrap;line-height:18px}
.elab.z{background:var(--flow-zone)}
.elab b{color:var(--ink);font-weight:600}

.step{position:absolute;background:var(--paper);border:1px solid #d9d9d9;border-radius:10px;display:flex;align-items:center;gap:12px;padding:0 14px}
.step .sic{width:38px;height:38px;border-radius:8px;background:var(--wash);display:grid;place-items:center;flex:none;color:var(--ink)}
.step .st{flex:1;min-width:0}
.step .sn{font-size:16px;font-weight:650;letter-spacing:-.01em;line-height:1.2}
.step .sw{font-size:13px;color:var(--ink-muted);margin-top:3px;line-height:1.3}
.step .sm{font-size:13px;color:var(--ink-muted);text-align:right;line-height:1.3;flex:none}
.tag{display:inline-flex;align-items:center;gap:5px;font-size:12.5px;font-weight:600;border:1px solid var(--rule);border-radius:999px;padding:2px 8px;color:var(--ink);background:var(--paper);white-space:nowrap}
.step.sel{border:2px solid var(--flow);box-shadow:0 0 0 4px var(--flow-wash)}
.port{position:absolute;width:10px;height:10px;border-radius:50%;background:var(--paper);border:2px solid var(--flow)}
.step.gate{background:var(--ink);border-color:var(--ink);color:#fff;border-radius:12px}
.step.gate .sic{background:#fff;color:var(--ink)}
.step.gate .sw{color:#c9c9c9}
.step.gate .tag{background:transparent;border-color:#5a5a5a;color:#fff}
.end{position:absolute;height:32px;border-radius:999px;border:1px solid var(--rule-strong);background:var(--paper);font-size:13.5px;
 font-weight:600;display:flex;align-items:center;gap:7px;padding:0 13px;white-space:nowrap}
.end .d{width:8px;height:8px;border-radius:50%;background:var(--ink)}
.end.m{border-color:var(--rule);color:var(--ink-muted);font-weight:500}
.end.m .d{background:transparent;border:1.5px solid var(--rule-strong)}

/* canvas overlays */
.chip{position:absolute;display:flex;align-items:center;gap:8px;height:34px;border:1px solid var(--rule);border-radius:8px;
 background:var(--paper);padding:0 12px;font-size:13.5px;font-weight:500}
.chip.bad{border-color:#efb8ae;background:var(--stop-wash);color:var(--stop-text);font-weight:600}
.zoom{position:absolute;display:flex;gap:8px;align-items:center}
.zoom .g{display:flex;border:1px solid var(--rule);border-radius:8px;background:var(--paper);height:36px;align-items:center}
.zoom .g span{display:grid;place-items:center;height:34px;min-width:36px;padding:0 8px;font-size:13.5px;font-weight:600}
.zoom .g span+span{border-left:1px solid var(--rule)}
.mini{position:absolute;width:150px;height:104px;border:1px solid var(--rule);border-radius:8px;background:var(--paper);overflow:hidden}
.mini i{position:absolute;display:block;border-radius:2px;background:#d4d4d4}
.mini i.g{background:var(--ink)}
.mini .vp{position:absolute;border:1.5px solid var(--flow);border-radius:3px;background:rgba(46,91,218,.06)}

/* refusal callout */
.callout{position:absolute;width:300px;background:var(--paper);border:1px solid #efb8ae;border-radius:10px;overflow:hidden}
.callout .ch{display:flex;gap:10px;align-items:flex-start;background:var(--stop-wash);padding:12px 14px;color:var(--stop-text)}
.callout .ch b{font-size:14.5px;font-weight:650;display:block;line-height:1.3}
.callout .cb{padding:10px 14px 12px;font-size:13.5px;line-height:1.45;color:var(--ink)}
.callout .cb p+p{margin-top:6px;color:var(--ink-muted)}
.callout .ca{display:flex;gap:8px;padding:0 14px 12px}
.callout{overflow:visible}.callout .ch{border-radius:10px 10px 0 0}
.callout .ptr{position:absolute;left:-7px;top:72px;width:12px;height:12px;background:var(--stop-wash);border-left:1px solid #efb8ae;border-bottom:1px solid #efb8ae;transform:rotate(45deg)}
.step.gate.refused{box-shadow:0 0 0 3px var(--paper),0 0 0 5px var(--stop)}

/* inspector */
.insp{position:absolute;right:0;top:56px;bottom:0;width:380px;border-left:1px solid var(--rule);background:var(--paper);overflow:hidden}
.ih{padding:16px 20px 14px;border-bottom:1px solid var(--rule);display:flex;gap:12px;align-items:center}
.ih .sic{width:40px;height:40px;border-radius:8px;background:var(--flow-wash);color:var(--flow);display:grid;place-items:center}
.ih .t{font-size:18px;font-weight:650;letter-spacing:-.015em}
.ih .k{font-size:13px;color:var(--ink-muted);margin-top:2px}
.sec{padding:14px 20px 4px}
.sec+.sec{border-top:1px solid var(--rule)}
.sec h3{font-size:14px;font-weight:650;margin-bottom:10px;display:flex;align-items:center;gap:8px}
.fld{margin-bottom:12px}
.fld label{display:block;font-size:13px;font-weight:600;margin-bottom:5px}
.sel2{height:38px;border:1px solid var(--rule-strong);border-radius:6px;display:flex;align-items:center;padding:0 10px;gap:8px;font-size:14px}
.sel2 .grow{flex:1}
.sel2 .h{color:var(--ink-muted);font-size:13px}
.row2{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.inp{height:38px;border:1px solid var(--rule-strong);border-radius:6px;display:flex;align-items:center;padding:0 10px;font-size:14px;gap:6px}
.inp .u{color:var(--ink-muted);font-size:13px}
.inp.err{border:2px solid var(--stop);padding:0 9px}
.ferr{display:flex;gap:7px;align-items:flex-start;color:var(--stop-text);font-size:13px;line-height:1.4;margin-top:6px;font-weight:500}
.need{display:flex;align-items:center;gap:8px;border:1px solid var(--rule);border-radius:6px;padding:7px 10px;font-size:13.5px;margin-bottom:6px}
.need .from{color:var(--ink-muted);margin-left:auto;font-size:13px}
.addl{font-size:13.5px;font-weight:600;color:var(--ink);display:flex;gap:6px;align-items:center;padding:4px 0 8px}
.cost{display:flex;align-items:baseline;gap:8px;margin-bottom:10px}
.cost .v{font-size:22px;font-weight:650;letter-spacing:-.015em}
.cost .l{font-size:13px;color:var(--ink-muted)}
.swbox{display:flex;gap:12px;align-items:flex-start;border:1px solid var(--rule);border-radius:8px;padding:10px 12px;background:var(--sunken)}
.tog{width:36px;height:20px;border-radius:10px;background:var(--ink);position:relative;flex:none;margin-top:1px;opacity:.55}
.tog:after{content:'';position:absolute;right:3px;top:3px;width:14px;height:14px;border-radius:50%;background:#fff}
.swbox b{font-size:14px;font-weight:600;display:flex;gap:6px;align-items:center}
.swbox p{font-size:13px;color:var(--ink-muted);line-height:1.4;margin-top:2px}
.next{display:flex;align-items:center;gap:10px;font-size:14px;padding:5px 0}
.next .p{width:58px;color:var(--ink-muted);font-size:13px}
.next .to{display:flex;align-items:center;gap:6px;font-weight:600}
.next .to:before{content:'';width:14px;height:1.5px;background:var(--flow)}

/* run */
.lamp{width:9px;height:9px;border-radius:50%;flex:none;display:inline-block}
.lamp.w{background:var(--amber)}.lamp.r{background:var(--live)}.lamp.f{background:var(--stop)}.lamp.d{background:#a3a3a3}
.runi{display:flex;gap:10px;padding:10px 10px;margin:0 8px;border-radius:6px;align-items:flex-start}
.runi.on{background:var(--wash)}
.runi .lamp{margin-top:6px}
.runi .rt{font-size:14px;font-weight:600;line-height:1.3}
.runi .rs{font-size:13px;color:var(--ink-muted);margin-top:2px}
.runi .rs.w{color:var(--amber-text)}.runi .rs.f{color:var(--stop-text)}.runi .rs.r{color:var(--live-text)}
.runbar{position:absolute;display:flex;align-items:center;gap:12px;height:44px;border:1px solid var(--rule);border-radius:10px;background:var(--paper);padding:0 6px 0 14px;font-size:14px}
.runbar .t{font-weight:650}
.runbar .m{color:var(--ink-muted)}
.st-done .sic{background:var(--wash)}
.step .ok{color:var(--ink);display:flex;align-items:center;gap:5px;justify-content:flex-end;font-weight:600}
.step.todo{border:1.5px dashed #c9c9c9;background:rgba(255,255,255,.7)}
.step.todo .sn{color:var(--ink-muted)}
.step.todo .sic{background:transparent;border:1px solid var(--rule);color:var(--ink-muted)}
.fail{color:var(--stop-text);font-weight:600}
.step.gate.wait{box-shadow:0 0 0 3px var(--paper),0 0 0 5px var(--amber)}
.wt{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;color:#ffd166}
.rp{padding:16px 20px;border-bottom:1px solid var(--rule)}
.badge2{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;border-radius:999px;padding:2px 9px}
.badge2.w{background:var(--amber-wash);color:var(--amber-text)}
.prev{border:1px solid var(--rule);border-radius:8px;overflow:hidden}
.prev .pt{padding:10px 12px;font-size:14px;line-height:1.5}
.prev .pm{padding:8px 12px;border-top:1px solid var(--rule);font-size:13px;color:var(--ink-muted);display:flex;justify-content:space-between}
.term{background:#171717;color:#e5e5e5;border-radius:8px;padding:10px 12px;font-family:'PlexMono',monospace;font-size:12.5px;line-height:1.6}
.term .g{color:#8f8f8f}
.term .a{color:#f2b52e}
.facts{display:grid;grid-template-columns:96px 1fr;row-gap:6px;font-size:13.5px}
.facts dt{color:var(--ink-muted)}
.facts dd{font-weight:500}
"""

STEPS = {
    'draft': ('pen', 'Draft copy', 'Writer, on Claude', '20 min limit'),
    'image': ('image', 'Generate image', 'Designer, on Imagen', None),
    'review': ('eye', 'Review', 'Editor, on Codex', 'Up to 2 rounds'),
    'gate': ('lock', 'Your approval', 'You see the post, image and time', None),
    'schedule': ('cal', 'Schedule', 'Waits for the time you approve', '08:00 to 20:00'),
    'publish': ('send', 'Publish', 'LinkedIn, company page', 'Checks it went live'),
}
ORDER = ['draft', 'image', 'review', 'gate', 'schedule', 'publish']
W, H, GW, GH = 340, 76, 384, 100


def geometry(cx):
    """Card boxes for a vertical definition centred on cx (canvas coordinates)."""
    ys = {'draft': 72, 'image': 184, 'review': 296, 'gate': 404, 'schedule': 564, 'publish': 676}
    g = {}
    for k in ORDER:
        w, h = (GW, GH) if k == 'gate' else (W, H)
        g[k] = (cx - w // 2, ys[k], w, h)
    g['barrier'] = 538
    g['end'] = (cx - 52, 788, 104, 32)
    return g


def edges_svg(g, run=None):
    """Transitions. run: set of traveled edge ids (blue, solid); the rest are ahead (grey, dashed)."""
    out, labels = [], []
    names = {('draft', 'image'): 'Done', ('image', 'review'): 'Done', ('review', 'gate'): 'Passed',
             ('gate', 'schedule'): 'Approved', ('schedule', 'publish'): 'At the set time', ('publish', 'end'): 'Live'}
    seq = ORDER + ['end']

    def style(eid):
        if run is None or eid in run:
            return 'stroke="#2e5bda" stroke-width="1.75" marker-end="url(#ab)"'
        return 'stroke="#b8b8b8" stroke-width="1.5" stroke-dasharray="5 5" marker-end="url(#ag)"'

    for a, b in zip(seq, seq[1:]):
        ax, ay, aw, ah = g[a]
        bx, by, bw, bh = g[b]
        x = ax + aw // 2
        out.append('<path d="M%d %d V%d" %s fill="none"/>' % (x, ay + ah, by - 2, style(a + '>' + b)))
        mid = (ay + ah + by) // 2
        zone = by > g['barrier']
        labels.append((x + 12, mid - 10, names[(a, b)], zone))
    # back edge: review changes asked -> draft
    rx, ry, rw, rh = g['review']
    dx, dy, dw, dh = g['draft']
    lx = rx + rw + 52
    out.append('<path d="M%d %d H%d Q%d %d %d %d V%d Q%d %d %d %d H%d" %s fill="none"/>' % (
        rx + rw, ry + rh // 2, lx - 10, lx, ry + rh // 2, lx, ry + rh // 2 - 10, dy + dh // 2 + 10, lx, dy + dh // 2,
        lx - 10, dy + dh // 2, dx + dw + 3, style('review>draft')))
    labels.append((lx + 10, (ry + dy + dh) // 2 + 2, 'Changes asked', False))
    # gate declined -> Dropped
    gx, gy, gw, gh = g['gate']
    out.append('<path d="M%d %d H%d" %s fill="none"/>' % (gx + gw, gy + gh // 2, gx + gw + 70, style('gate>dropped')))
    labels.append((gx + gw + 10, gy + gh // 2 - 30, 'Declined', False))
    # publish failed -> stopped
    px, py, pw, ph = g['publish']
    out.append('<path d="M%d %d H%d" %s fill="none"/>' % (px + pw, py + ph // 2, px + pw + 70, style('publish>stopped')))
    labels.append((px + pw + 10, py + ph // 2 - 30, 'Failed', True))
    svg = ('<svg class="edges" width="1" height="1"><defs>'
           '<marker id="ab" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
           '<path d="M1 1 9 5 1 9Z" fill="#2e5bda"/></marker>'
           '<marker id="ag" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
           '<path d="M1 1 9 5 1 9Z" fill="#b8b8b8"/></marker></defs>%s</svg>' % ''.join(out))
    lab = ''.join('<div class="elab%s" style="left:%dpx;top:%dpx">%s</div>' % (' z' if z else '', x, y, t)
                  for x, y, t, z in labels)
    ends = ('<div class="end m" style="left:%dpx;top:%dpx">Dropped</div>' % (gx + gw + 74, gy + gh // 2 - 16) +
            '<div class="end m" style="left:%dpx;top:%dpx">Stopped, you are told</div>' % (px + pw + 74, py + ph // 2 - 16))
    return svg + lab + ends


def box(k, g, cls='', meta=None, who=None, extra=''):
    icon, name, w, m = STEPS[k]
    x, y, wd, h = g[k]
    meta = m if meta is None else meta
    who = w if who is None else who
    mh = '<div class="sm">%s</div>' % meta if meta else ''
    return ('<div class="step %s" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"><div class="sic">%s</div>'
            '<div class="st"><div class="sn">%s</div><div class="sw">%s</div></div>%s%s</div>'
            % (cls + (' gate' if k == 'gate' else ''), x, y, wd, h, ic(icon, 20), name, who, mh, extra))


def zone(g, label=True):
    lab = ('<div class="zl">%s<span>Runs only after you approve</span></div>' % ic('lock', 16)) if label else ''
    return '<div class="zone" style="top:%dpx">%s</div>' % (g['barrier'], lab)


def rail(active='flow'):
    items = [('grid', 'Overview'), ('term', 'Runs'), ('inbox', 'Decisions'), None, ('list', 'Backlog'),
             ('users', 'Team'), ('flow', 'Workflows'), ('chart', 'Usage'), None, ('gear', 'Configuration')]
    h = ['<nav class="rail"><span class="dot"></span>']
    for it in items:
        if it is None:
            h.append('<span class="sep"></span>')
            continue
        b = '<span class="badge">5</span>' if it[0] == 'inbox' else ''
        h.append('<span class="r%s" title="%s">%s%s</span>' % (' on' if it[0] == active else '', it[1], ic(it[0], 19), b))
    h.append('<span class="av">DG</span></nav>')
    return ''.join(h)


def top(tab, state):
    runs_on = tab == 'runs'
    return ('<header class="top"><span class="ibtn">%s</span>'
            '<div class="crumb"><span>Workflows</span><span class="slash">/</span></div>'
            '<div class="wf">Social post %s</div>'
            '<div class="ver">%s</div><div class="grow"></div>'
            '<div class="seg"><span class="%s">Design</span><span class="%s">Runs <span class="n">5</span></span></div>'
            '<div class="grow"></div>%s</header>'
            % (ic('panel', 19), ic('chev', 16), state, '' if runs_on else 'on', 'on' if runs_on else '',
               '' if runs_on else
               '<span class="ibtn b" title="Undo">%s</span><span class="ibtn b dis" title="Redo">%s</span>'
               '<span class="btn p">Save as version 4</span>' % (ic('undo', 17), ic('redo', 17))))


def palette():
    groups = [
        ('Work', [('pen', 'Write', 'Drafts text with a writer'), ('eye', 'Review', 'Checks work against your criteria'),
                  ('image', 'Generate image or video', 'Paid, asks you each time'),
                  ('file', 'Render pages', 'Turns a document into pages')]),
        ('Flow', None),
        ('You', [('lock', 'Your approval', 'Required before anything goes out')]),
        ('Timing', [('cal', 'Schedule', 'Waits for a time you approve')]),
        ('Going out', [('send', 'Publish', 'Posts to a channel'), ('rocket', 'Deploy', 'Releases a build you approved'),
                       ('box', 'Deliver files', 'Sends finished files to you')]),
    ]
    h = ['<aside class="left"><h2>Add a step</h2><div class="sub">Drag a step onto a connection, or pick one and press '
         '<span class="kbd">Enter</span></div><div class="search">%s<span>Find a step type</span>'
         '<span class="grow"></span><span class="kbd">/</span></div>' % ic('search', 16)]
    for gname, items in groups:
        if items is None:
            # Check and Join as one compact row: a full group would push Deliver files and the shortcut line
            # off a 900 px screen (measured: 126 px over).
            h.append('<div class="flowrow"><span class="fl">Flow</span>%s</div>' % ''.join(
                '<span class="ft" title="%s"><span class="pic">%s</span>%s</span>' % (d, ic(i, 15), t) for i, t, d in
                [('split', 'Check', 'Routes work by a rule you set'), ('merge', 'Join', 'Waits for every branch')]))
            continue
        h.append('<div class="grp">%s</div>' % gname)
        for icon, t, d in items:
            cls = ' gate' if icon == 'lock' else ('')
            h.append('<div class="pi%s"><div class="pic">%s</div><div><div class="pt">%s</div><div class="pd">%s</div></div></div>'
                     % (cls, ic(icon, 16), t, d))
    h.append('<div class="foot">%s</div></aside>' % (
        'Press <span class="kbd">?</span> for every shortcut. Arrow keys move between steps; '
        '<span class="kbd">C</span> connects the selected step.'))
    return ''.join(h)


def zoombar(x, y, pct='100%'):
    return ('<div class="zoom" style="left:%dpx;top:%dpx"><div class="g"><span>%s</span><span class="num">%s</span><span>%s</span></div>'
            '<div class="g"><span style="display:flex;gap:6px;align-items:center">%s Fit</span></div></div>' % (x, y, ic('minus', 16), pct, ic('plus', 16), ic('fit', 15)))


def minimap(x, y, vp=None):
    # 1:8 sketch of the vertical definition
    bars = ''.join('<i style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"%s></i>' % (
        l, t, w, h, ' class="g"' if gate else '') for l, t, w, h, gate in
        [(55, 10, 38, 9, 0), (55, 24, 38, 9, 0), (55, 38, 38, 9, 0), (52, 52, 44, 12, 1), (55, 70, 38, 9, 0), (55, 84, 38, 9, 0)])
    l, t, w, h = vp or (14, 4, 122, 96)
    return '<div class="mini" style="left:%dpx;top:%dpx">%s<span class="vp" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"></span></div>' % (
        x, y, bars, l, t, w, h)


def page(body, phone=False, title='VELDO-0246'):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>%s</title><style>%s</style></head>'
            '<body class="%s">%s</body></html>' % (title, CSS, 'phone' if phone else '', body))


# Section: (a) the canvas with social post open
def screen_a():
    cw = 1440 - 300
    g = geometry(500)
    cards = ''.join(box(k, g, meta=('<span class="tag">%s Paid, asks you</span>' % ic('coin', 14)) if k == 'image' else
                         ('<span class="tag">%s Always required</span>' % ic('lock', 13)) if k == 'gate' else None)
                    for k in ORDER)
    end = '<div class="end" style="left:%dpx;top:%dpx"><span class="d"></span>Published</div>' % g['end'][:2]
    chip = '<div class="chip" style="left:16px;top:16px">%s Ready to save: every step is connected and your approval comes before Publish</div>' % ic('check', 16)
    canvas = ('<main class="canvas" style="left:300px;width:%dpx">%s%s%s%s%s%s%s</main>'
              % (cw, zone(g), edges_svg(g), cards, end, chip, zoombar(16, 796), minimap(cw - 166, 724)))
    return page(rail() + top('design', '<b>Version 3</b><span class="edited">Edited, not saved</span>') + palette() + canvas)


# Section: (b) a step selected, inspector, validation
def screen_b():
    cw = 1440 - 300 - 380
    g = geometry(300)
    x, y, w, h = g['image']
    ports = ('<span class="port" style="left:%dpx;top:%dpx"></span><span class="port" style="left:%dpx;top:%dpx"></span>'
             % (x + w // 2 - 5, y - 6, x + w // 2 - 5, y + h - 4))
    cards = ''.join(box(k, g, cls='sel' if k == 'image' else 'refused' if k == 'gate' else '',
                        meta=('<span class="tag">%s Paid, asks you</span>' % ic('coin', 14)) if k == 'image' else
                        ('<span class="tag">%s Always required</span>' % ic('lock', 13)) if k == 'gate' else None)
                    for k in ORDER)
    gx, gy, gw, gh = g['gate']
    callout = ('<div class="callout" style="left:%dpx;top:%dpx;width:244px"><span class="ptr"></span><div class="ch">%s<div><b>Your approval can\'t be removed</b></div>'
               '<span class="grow"></span>%s</div><div class="cb"><p>Every social post needs your approval before Publish, '
               'so nothing goes out that you have not seen.</p><p>You can move it earlier, or add a second approval. '
               'Your workflow is unchanged.</p></div></div>' % (gx + gw + 16, gy - 26, ic('lock', 17), ic('x', 16)))
    chip = '<div class="chip bad" style="left:16px;top:16px">%s 1 thing to fix before saving: Generate image, spend limit</div>' % ic('alert', 16)
    end = '<div class="end" style="left:%dpx;top:%dpx"><span class="d"></span>Published</div>' % g['end'][:2]
    canvas = ('<main class="canvas" style="left:300px;width:%dpx">%s%s%s%s%s%s%s%s</main>'
              % (cw, zone(g), edges_svg(g), cards, ports, end, callout, chip, zoombar(16, 796)))
    insp = ('<aside class="insp"><div class="ih"><div class="sic">%s</div><div><div class="t">Generate image</div>'
            '<div class="k">Generate image or video step</div></div><span class="grow"></span>'
            '<span class="ibtn b" title="Duplicate">%s</span><span class="ibtn b" title="Remove step">%s</span></div>'
            '<div class="sec"><h3>Who does it</h3>'
            '<div class="fld"><label>Role</label><div class="sel2"><span class="grow">Designer</span><span class="h">your team</span>%s</div></div>'
            '<div class="fld"><label>Engine</label><div class="sel2"><span class="grow">Imagen</span><span class="h">media server</span>%s</div></div></div>'
            '<div class="sec"><h3>What it needs</h3>'
            '<div class="need">%s The post copy<span class="from">from Draft copy</span></div>'
            '<div class="need">%s Brand guide<span class="from">project file</span></div>'
            '<div class="addl">%s Add something it needs</div></div>'
            '<div class="sec"><h3>Limits</h3><div class="row2">'
            '<div class="fld"><label>Images</label><div class="inp num">3</div></div>'
            '<div class="fld"><label>Time</label><div class="inp num">10<span class="u">min</span></div></div>'
            '<div class="fld"><label>Retries</label><div class="inp num">1</div></div></div></div>'
            '<div class="sec"><h3>Cost and approval</h3>'
            '<div class="cost"><span class="v num">$0.04</span><span class="l">an image, so up to $0.12 a run</span></div>'
            '<div class="fld"><label>Spend limit a run</label><div class="inp err num">$<span>0.10</span></div>'
            '<div class="ferr">%s<span>3 images can cost $0.12. Raise the limit to $0.12, or lower Images to 2.</span></div></div>'
            '<div class="swbox"><span class="tog"></span><div><b>Ask me before each use %s</b>'
            '<p>Always on for paid steps. You see the cost and approve it, on your phone too.</p></div></div></div>'
            '</aside>' % (ic('image', 20), ic('copy', 16), ic('trash', 16), ic('chev', 16), ic('chev', 16),
                          ic('link', 15), ic('file', 15), ic('plus', 15), ic('alert', 15), ic('lock', 13)))
    return page(rail() + top('design', '<b>Version 3</b><span class="edited">Edited, not saved</span>') + palette() + canvas + insp)


# Section: (c) a run on the same canvas
RUNS = [('w', 'Lisbon eSIM tips', 'Waiting on you, 14 min', True), ('r', 'Packing list for Tokyo', 'Running: Generate image', False),
        ('f', 'Weekend in Rome', 'Failed at Publish, 09:02', False), ('d', 'Data roaming myths', 'Published Tue 09:00', False),
        ('d', 'Airport wifi or eSIM', 'Published Mon 12:30', False)]


def run_list():
    h = ['<aside class="left"><h2>Runs</h2><div class="sub">Each post made with this workflow</div>']
    for k, t, s, on in RUNS:
        h.append('<div class="runi%s"><span class="lamp %s"></span><div><div class="rt">%s</div><div class="rs %s">%s</div></div></div>'
                 % (' on' if on else '', k, t, k if k != 'd' else '', s))
    h.append('<div class="foot">All runs use version 3. Saving a new version changes later runs only.</div></aside>')
    return ''.join(h)


def run_cards(g):
    c = []
    done = '<div class="sm"><span class="ok">%s Done</span>%s</div>'
    c.append(box('draft', g, cls='st-done', meta=done % (ic('check', 15), '2 rounds, 6 min')))
    c.append(box('image', g, cls='st-done', who='2 images, $0.08 spent',
                 meta=done % (ic('check', 15), '<span class="fail">1 attempt failed</span>')))
    c.append(box('review', g, cls='st-done', meta=done % (ic('check', 15), 'Passed round 2')))
    c.append(box('gate', g, cls='wait', meta='<span class="wt"><span class="lamp w"></span>Waiting on you</span>',
                 who='Since 10:42, 14 min'))
    c.append(box('schedule', g, cls='todo', meta='Not started'))
    c.append(box('publish', g, cls='todo', meta='Not started'))
    c.append('<div class="end m" style="left:%dpx;top:%dpx"><span class="d"></span>Published</div>' % g['end'][:2])
    return ''.join(c)


def screen_c():
    cw = 1440 - 300 - 380
    g = geometry(300)
    traveled = {'draft>image', 'image>review', 'review>gate', 'review>draft'}
    bar = ('<div class="runbar" style="left:16px;top:12px;right:16px"><span class="lamp w"></span><span class="t">Lisbon eSIM tips</span>'
           '<span class="m">Step 4 of 6, version 3</span><span class="grow"></span><span class="btn q">%s Open terminal <span class="kbd">T</span></span></div>'
           % ic('term', 16))
    canvas = ('<main class="canvas" style="left:300px;width:%dpx">%s%s%s%s%s</main>'
              % (cw, zone(g), edges_svg(g, traveled), run_cards(g), bar, zoombar(16, 796)))
    art = ('<svg width="338" height="150" viewBox="0 0 338 150" style="display:block">'
           '<rect width="338" height="150" fill="#dfe8fb"/><rect y="98" width="338" height="52" fill="#2e5bda"/>'
           '<circle cx="268" cy="44" r="20" fill="#f2b52e"/>'
           '<path d="M0 98 40 70 70 84 104 56 140 80 176 62 214 86 250 70 300 92 338 78V98Z" fill="#9bb2ee"/>'
           '<rect x="120" y="76" width="96" height="40" rx="6" fill="#f2a900"/><rect x="128" y="84" width="18" height="14" rx="2" fill="#fff"/>'
           '<rect x="152" y="84" width="18" height="14" rx="2" fill="#fff"/><rect x="176" y="84" width="18" height="14" rx="2" fill="#fff"/>'
           '<rect x="120" y="116" width="96" height="4" fill="#171717"/><path d="M168 76V54" stroke="#171717" stroke-width="2"/></svg>')
    panel = ('<aside class="insp"><div class="rp"><div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
             '<span class="badge2 w"><span class="lamp w"></span>Waiting on you</span><span style="font-size:13px;color:var(--ink-muted)">since 10:42</span></div>'
             '<div style="font-size:18px;font-weight:650;letter-spacing:-.015em">Approve this post?</div>'
             '<div style="font-size:13.5px;color:var(--ink-muted);margin-top:4px;line-height:1.45">Review passed it in round 2. '
             'Nothing is posted until you approve.</div></div>'
             '<div class="rp"><div class="prev">%s<div class="pt">Landing in Lisbon this week? Skip the airport SIM queue: '
             'install your eSIM before you fly and you are online the moment the wheels touch down.</div>'
             '<div class="pm"><span>LinkedIn, company page</span><span>212 characters</span></div></div>'
             '<dl class="facts" style="margin-top:12px"><dt>Posts at</dt><dd>Thu 6 Nov, 09:00 Lisbon</dd>'
             '<dt>Spent so far</dt><dd class="num">$0.08 of $0.12</dd></dl>'
             '<span class="btn p lg" style="display:flex;justify-content:center;margin-top:14px">Approve</span>'
             '<div style="display:flex;gap:8px;margin-top:8px"><span class="btn" style="flex:1;justify-content:center">Ask for changes</span>'
             '<span class="btn q" style="flex:1;justify-content:center">Decline</span></div></div>'
             '<div class="rp" style="border-bottom:0"><div style="display:flex;align-items:center;margin-bottom:8px">'
             '<b style="font-size:14px;font-weight:650">Live record</b><span class="grow"></span>'
             '<span style="font-size:13.5px;font-weight:600;display:flex;gap:6px;align-items:center">%s Open terminal</span></div>'
             '<div class="term"><div><span class="g">10:39:51</span> review: round 2 passed</div>'
             '<div><span class="g">10:42:03</span> approval asked</div>'
             '<div><span class="g">10:42:03</span> <span class="a">waiting for the owner</span></div></div></div></aside>'
             % (art, ic('term', 16)))
    return page(rail() + top('runs', '<b>Version 3</b><span>Saved</span>') + run_list() + canvas + panel)


# Section: (d) phone view of (c)
PHONE_CSS = """
.ptop{height:56px;border-bottom:1px solid var(--rule);display:flex;align-items:center;gap:6px;padding:0 10px 0 6px}
.ptop .t{font-size:16px;font-weight:650;letter-spacing:-.01em;line-height:1.2}
.ptop .s{font-size:12.5px;color:var(--ink-muted)}
.pstat{display:flex;align-items:center;gap:8px;padding:10px 16px;border-bottom:1px solid var(--rule);font-size:13.5px}
.track{position:relative;padding:8px 16px 0 16px}
.tr{display:flex;align-items:center;gap:12px;height:42px;position:relative}
.tr .n{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;background:var(--paper);border:1.5px solid var(--flow);color:var(--flow);flex:none;z-index:1}
.tr .nm{font-size:14.5px;font-weight:600}
.tr .x{margin-left:auto;font-size:13px;color:var(--ink-muted)}
.tr .x.fail{color:var(--stop-text);font-weight:600}
.tr.todo .n{border:1.5px dashed #b8b8b8;color:var(--ink-muted)}
.tr.todo .nm{color:var(--ink-muted);font-weight:500}
.line{position:absolute;left:28px;width:2px;background:var(--flow)}
.line.ahead{background:repeating-linear-gradient(#c4c4c4 0 4px,transparent 4px 8px)}
.pg{margin:6px 0 6px 0;background:var(--ink);color:#fff;border-radius:12px;padding:12px;position:relative;z-index:1;box-shadow:0 0 0 3px var(--paper),0 0 0 5px var(--amber)}
.pg .h{display:flex;align-items:center;gap:10px}
.pg .h .sic{width:30px;height:30px;border-radius:7px;background:#fff;color:var(--ink);display:grid;place-items:center}
.pg .h b{font-size:15.5px;font-weight:650}
.pg .card{background:#fff;color:var(--ink);border-radius:8px;overflow:hidden;margin-top:10px}
.pg .card .pt{padding:9px 11px;font-size:13.5px;line-height:1.45}
.pg .meta{font-size:12.5px;color:#d4d4d4;margin-top:8px;display:flex;justify-content:space-between}
.act{position:absolute;left:0;right:0;bottom:64px;border-top:1px solid var(--rule);background:var(--paper);padding:10px 16px;display:flex;flex-wrap:wrap;gap:8px}
.bnav{position:absolute;left:0;right:0;bottom:0;height:64px;border-top:1px solid var(--rule);display:grid;grid-template-columns:repeat(4,1fr);background:var(--paper)}
.bnav span{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;font-size:12px;color:var(--ink-muted);position:relative}
.bnav span.on{color:var(--ink);font-weight:600}
.bnav .badge{position:absolute;top:8px;left:54%;min-width:16px;height:16px;border-radius:8px;background:var(--amber);color:var(--ink);font-size:11px;font-weight:650;display:grid;place-items:center}
"""


def screen_d():
    art = ('<svg width="100%" height="96" viewBox="0 0 338 96" preserveAspectRatio="xMidYMid slice" style="display:block">'
           '<rect width="338" height="96" fill="#dfe8fb"/><rect y="66" width="338" height="30" fill="#2e5bda"/>'
           '<circle cx="270" cy="30" r="14" fill="#f2b52e"/>'
           '<path d="M0 66 40 46 70 56 104 36 140 52 176 40 214 58 250 46 300 60 338 52V66Z" fill="#9bb2ee"/>'
           '<rect x="124" y="48" width="84" height="30" rx="5" fill="#f2a900"/><rect x="131" y="54" width="16" height="11" rx="2" fill="#fff"/>'
           '<rect x="153" y="54" width="16" height="11" rx="2" fill="#fff"/><rect x="175" y="54" width="16" height="11" rx="2" fill="#fff"/></svg>')
    done = [('Draft copy', '2 rounds, 6 min', ''), ('Generate image', '1 failed, retried', 'f'), ('Review', 'Passed round 2', '')]
    rows = ''.join('<div class="tr"><span class="n">%s</span><span class="nm">%s</span><span class="x%s">%s</span></div>'
                   % (ic('check', 14), n, ' fail' if f else '', x) for n, x, f in done)
    todo = ''.join('<div class="tr todo"><span class="n">%s</span><span class="nm">%s</span><span class="x">Not started</span></div>'
                   % (ic(i, 13), n) for i, n in [('cal', 'Schedule, Thu 09:00'), ('send', 'Publish')])
    body = ('<style>%s</style><header class="ptop"><span class="ibtn">%s</span><div><div class="t">Lisbon eSIM tips</div>'
            '<div class="s">Social post, step 4 of 6</div></div><span class="grow"></span>'
            '<span class="btn q" style="height:34px;padding:0 10px">%s Terminal</span></header>'
            '<div class="pstat"><span class="badge2 w"><span class="lamp w"></span>Waiting on you</span>'
            '<span style="color:var(--ink-muted)">14 min</span><span class="grow"></span>'
            '<span style="font-weight:600;display:flex;align-items:center;gap:5px">%s Canvas</span></div>'
            '<div class="track"><span class="line" style="top:29px;height:136px"></span><span class="line ahead" style="top:402px;height:66px"></span>'
            '%s<div class="pg"><div class="h"><span class="sic">%s</span><b>Your approval</b><span class="grow"></span>'
            '<span style="font-size:12.5px;color:#d4d4d4">Always required</span></div>'
            '<div class="card">%s<div class="pt">Landing in Lisbon this week? Skip the airport SIM queue: install your eSIM '
            'before you fly and you are online the moment the wheels touch down.</div></div>'
            '<div class="meta"><span>LinkedIn, Thu 6 Nov, 09:00</span><span class="num">$0.08 spent</span></div></div>'
            '%s</div>'
            '<div class="act"><span class="btn p lg" style="width:100%%;justify-content:center">Approve</span>'
            '<span class="btn" style="flex:1;justify-content:center">Ask for changes</span><span class="btn q" style="flex:1;justify-content:center">Decline</span></div>'
            '<nav class="bnav"><span>%sOverview</span><span class="on">%sRuns</span><span>%sDecisions<i class="badge">5</i></span>'
            '<span>%sMore</span></nav>'
            % (PHONE_CSS, ic('back', 20), ic('term', 15), ic('flow', 15), rows, ic('lock', 16), art, todo,
               ic('grid', 20), ic('term', 20), ic('inbox', 20), ic('more', 20)))
    return page(body, phone=True)


# Section: (e) and (f) conditions and parallel branches (owner, Telegram 39079: "what if steps are conditional?")
# The flow is drawn at 85 percent (Fit) in its own layer, so every box below is in canvas units.
EF_CSS = """
.layer{position:absolute;left:0;top:0;transform-origin:0 0}
.canvas.z85{background-size:17px 17px}
.step.path{border:2px solid var(--stop);box-shadow:0 0 0 4px var(--stop-wash)}
.elab.bad{color:var(--stop-text);font-weight:600}
.end.path{border:2px solid var(--stop);box-shadow:0 0 0 3px var(--stop-wash)}
.skip{position:absolute;display:flex;align-items:center;gap:6px;height:28px;padding:0 10px;border-radius:999px;background:var(--stop);
 color:#fff;font-size:13px;font-weight:650;white-space:nowrap}
.rule .inp,.rule .sel2{height:38px}
.chips{min-height:38px;border:1px solid var(--rule-strong);border-radius:6px;display:flex;flex-wrap:wrap;gap:6px;padding:6px 8px;align-items:center}
.chips .tk{display:inline-flex;align-items:center;gap:4px;font-size:13.5px;font-weight:500;background:var(--wash);border-radius:4px;padding:2px 4px 2px 8px}
.chips .tk svg{color:var(--ink-muted)}
.chips .add{font-size:13.5px;color:var(--ink-muted);padding-left:2px}
.hint{font-size:13px;color:var(--ink-muted);line-height:1.4;margin-top:6px}
.br{display:flex;align-items:center;gap:10px;border:1px solid var(--rule);border-radius:6px;padding:8px 10px;font-size:14px;margin-bottom:6px}
.br .bl{font-weight:650;min-width:72px;display:flex;align-items:center;gap:8px}
.br .bl:before{content:'';width:14px;height:1.5px;background:var(--flow)}
.br .to{display:flex;align-items:center;gap:6px}
.br .then{color:var(--ink-muted);font-size:13px}
.br .lk{margin-left:auto;color:var(--ink-muted);display:flex;align-items:center;gap:4px;font-size:12.5px}
.br.err{border:2px solid var(--stop);padding:7px 9px}
.br.err .bl:before{background:var(--stop)}
.note{display:flex;gap:8px;align-items:flex-start;font-size:13px;color:var(--ink);line-height:1.4;padding:4px 0 12px}
.refuse{border-bottom:1px solid var(--rule)}
.refuse .ch{display:flex;gap:10px;align-items:flex-start;background:var(--stop-wash);padding:14px 20px;color:var(--stop-text)}
.refuse .ch b{font-size:15px;font-weight:650;line-height:1.3;display:block}
.refuse .cb{padding:12px 20px 4px;font-size:13.5px;line-height:1.45}
.trail{position:relative;margin:10px 0 4px;padding-left:2px}
.trail .tr{display:flex;align-items:center;gap:10px;height:30px;font-size:14px;position:relative}
.trail .tr .n{width:12px;height:12px;border-radius:50%;background:var(--paper);border:2px solid #b8b8b8;flex:none;margin-left:5px;z-index:1}
.trail .tr .o{margin-left:auto;font-size:13px;color:var(--ink-muted)}
.trail .tr.on .n{border-color:var(--stop)}
.trail .tr.on .o{color:var(--stop-text);font-weight:600}
.trail .tr.miss{color:var(--stop-text);font-weight:600}
.trail .tr.miss .n{width:22px;height:22px;margin-left:0;border:1.5px dashed var(--stop);display:grid;place-items:center;color:var(--stop)}
.trail .ln{position:absolute;left:12px;width:2px}
.refuse .ca{display:flex;flex-direction:column;gap:8px;padding:8px 20px 16px}
.refuse .ca .btn{justify-content:center}
"""

EF_CX = 400
EF = {
    'start': (EF_CX - 36, 64, 72, 30),
    'draft': (EF_CX - 348, 126, 340, 76), 'image': (EF_CX + 8, 126, 340, 76),
    'join': (EF_CX - 130, 238, 260, 60),
    'check': (EF_CX - 150, 330, 300, 76), 'legal': (EF_CX + 210, 330, 240, 76),
    'review': (EF_CX - 170, 450, 340, 76), 'gate': (EF_CX - 192, 562, 384, 100),
    'schedule': (EF_CX - 170, 718, 340, 76), 'publish': (EF_CX - 170, 826, 340, 76),
    'end': (EF_CX - 52, 934, 104, 32), 'barrier': 694,
}
EF_STEPS = dict(STEPS, join=('merge', 'Join', 'Waits for copy and image', None),
                check=('split', 'Mentions prices?', 'Looks at the post copy', None),
                legal=('eye', 'Legal review', 'Compliance, on Claude', None))
EF_S = 0.85


def ef_box(k, cls='', meta=None, extra=''):
    icon, name, who, m = EF_STEPS[k]
    x, y, w, h = EF[k]
    meta = m if meta is None else meta
    mh = '<div class="sm">%s</div>' % meta if meta else ''
    return ('<div class="step %s" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx"><div class="sic">%s</div>'
            '<div class="st"><div class="sn">%s</div><div class="sw">%s</div></div>%s%s</div>'
            % (cls + (' gate' if k == 'gate' else ''), x, y, w, h, ic(icon, 20), name, who, mh, extra))


def ef_edges(bad=False):
    """bad: Legal review's Cleared is wired straight to Schedule, around the approval (screen f)."""
    B = 'stroke="#2e5bda" stroke-width="1.75" fill="none"'
    R = 'stroke="#d63b2a" stroke-width="2.5" fill="none"'
    cx, out, labels = EF_CX, [], []

    def e(d, red=False, arrow=True):
        out.append('<path d="%s" %s%s/>' % (d, R if red else B, (' marker-end="url(#%s)"' % ('ar' if red else 'ab')) if arrow else ''))

    def lab(x, y, t, zone=False, red=False):
        labels.append('<div class="elab%s%s" style="left:%dpx;top:%dpx">%s</div>' % (' z' if zone else '', ' bad' if red else '', x, y, t))
    L, Rt = cx - 174, cx + 182
    # fork: one start, both at once
    e('M%d 94 V110' % cx, arrow=False)
    e('M%d 110 H%d' % (L, Rt), arrow=False)
    e('M%d 110 V124' % L)
    e('M%d 110 V124' % Rt)
    lab(cx + 48, 70, 'Both at once')
    # merge into Join
    e('M%d 202 V222 M%d 202 V222 M%d 222 H%d' % (L, Rt, L, Rt), arrow=False)
    e('M%d 222 V236' % cx)
    lab(L + 12, 203, 'Done')
    lab(Rt + 12, 203, 'Done')
    e('M%d 298 V328' % cx)
    lab(cx + 12, 303, 'Both done')
    # the Check: Yes to Legal review, Otherwise straight on
    e('M%d 368 H%d' % (cx + 150, cx + 207), red=bad)
    lab(cx + 158, 340, 'Yes', red=bad)
    e('M%d 406 V448' % cx)
    lab(cx + 12, 416, 'Otherwise')
    if bad:
        # Cleared rewired around the approval, to Schedule
        e('M%d 368 H%d Q%d 368 %d 378 V746 Q%d 756 %d 756 H%d' % (cx + 450, cx + 470, cx + 480, cx + 480, cx + 480, cx + 470, cx + 173), red=True)
        lab(cx + 412, 450, 'Cleared', red=True)
        e('M%d 794 V824' % cx, red=True)
        e('M%d 902 V932' % cx, red=True)
    else:
        e('M%d 406 V478 Q%d 488 %d 488 H%d' % (cx + 330, cx + 330, cx + 320, cx + 173))
        lab(cx + 342, 424, 'Cleared')
        e('M%d 794 V824' % cx)
        e('M%d 902 V932' % cx)
    # review loop back to Draft copy (on the left, where Draft copy is)
    e('M%d 488 H30 Q20 488 20 478 V176 Q20 166 30 166 H%d' % (cx - 170, cx - 348 - 3))
    lab(30, 392, 'Changes asked')
    e('M%d 526 V560' % cx)
    lab(cx + 12, 533, 'Passed')
    e('M%d 662 V716' % cx)
    lab(cx + 12, 680, 'Approved', zone=True)
    lab(cx + 12, 800, 'At the set time', zone=True, red=bad)
    lab(cx + 12, 908, 'Live', zone=True, red=bad)
    gx, gy, gw, gh = EF['gate']
    e('M%d %d H%d' % (gx + gw, gy + gh // 2, gx + gw + 70))
    lab(gx + gw + 10, gy + gh // 2 - 30, 'Declined')
    px, py, pw, ph = EF['publish']
    e('M%d %d H%d' % (px + pw, py + ph // 2, px + pw + 70))
    lab(px + pw + 10, py + ph // 2 - 30, 'Failed', zone=True)
    svg = ('<svg class="edges" width="1" height="1"><defs>'
           '<marker id="ab" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
           '<path d="M1 1 9 5 1 9Z" fill="#2e5bda"/></marker>'
           '<marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
           '<path d="M1 1 9 5 1 9Z" fill="#d63b2a"/></marker></defs>%s</svg>' % ''.join(out))
    ends = ('<div class="end m" style="left:%dpx;top:%dpx">Start</div>' % EF['start'][:2] +
            '<div class="end m" style="left:%dpx;top:%dpx">Dropped</div>' % (gx + gw + 74, gy + gh // 2 - 16) +
            '<div class="end m" style="left:%dpx;top:%dpx">Stopped, you are told</div>' % (px + pw + 74, py + ph // 2 - 16) +
            '<div class="end%s" style="left:%dpx;top:%dpx"><span class="d"></span>Published</div>' % (' path' if bad else '', EF['end'][0], EF['end'][1]))
    return svg + ''.join(labels) + ends


def ef_canvas(bad):
    cw, ch = 1440 - 300 - 380, 900 - 56
    paid = '<span class="tag">%s Paid, asks you</span>' % ic('coin', 14)
    lockt = '<span class="tag">%s Always required</span>' % ic('lock', 13)
    on_path = {'check', 'legal', 'schedule', 'publish'} if bad else set()
    cls = lambda k: ('sel' if k == ('legal' if bad else 'check') else '') + (' path' if k in on_path and not (bad and k == 'legal') else '')
    cards = ''.join(ef_box(k, cls=cls(k), meta=paid if k == 'image' else lockt if k == 'gate' else None)
                    for k in ['draft', 'image', 'join', 'check', 'legal', 'review', 'gate', 'schedule', 'publish'])
    sk = ('<div class="skip" style="left:%dpx;top:%dpx">%s Skips your approval</div>' % (EF_CX + 318, EF['barrier'] - 14, ic('alert', 14))
          if bad else '')
    sx, sy, sw, sh = EF[('legal' if bad else 'check')]
    ports = ''.join('<span class="port" style="left:%dpx;top:%dpx"></span>' % p for p in
                    [(sx + sw // 2 - 5, sy - 6), (sx + sw // 2 - 5, sy + sh - 4), (sx + sw - 4, sy + sh // 2 - 5)])
    layer = ('<div class="layer" style="width:%dpx;height:%dpx;transform:scale(%s)">%s%s%s%s%s</div>'
             % (round(cw / EF_S), round(ch / EF_S), EF_S, '<div class="zone" style="top:%dpx">%s</div>' % (
                 EF['barrier'], '<div class="zl">%s<span>Runs only after you approve</span></div>' % ic('lock', 16)),
                ef_edges(bad), cards, ports, sk))
    chip = ('<div class="chip bad" style="left:16px;top:16px">%s Not saved: 1 path reaches Publish without your approval</div>' % ic('alert', 16)
            if bad else
            '<div class="chip" style="left:16px;top:16px">%s Ready to save: every path passes your approval before Publish</div>' % ic('check', 16))
    return '<main class="canvas z85" style="left:300px;width:%dpx">%s%s%s</main>' % (cw, layer, chip, zoombar(16, 796, '85%'))


def screen_e():
    insp = ('<aside class="insp"><div class="ih"><div class="sic">%s</div><div><div class="t">Mentions prices?</div>'
            '<div class="k">Check step</div></div><span class="grow"></span>'
            '<span class="ibtn b" title="Duplicate">%s</span><span class="ibtn b" title="Remove step">%s</span></div>'
            '<div class="sec rule"><h3>The rule</h3>'
            '<div class="fld"><label>Look at</label><div class="sel2"><span class="grow">The post copy</span><span class="h">from Draft copy</span>%s</div></div>'
            '<div class="fld"><label>Test</label><div class="sel2"><span class="grow">Mentions any of</span>%s</div>'
            '<div class="hint">Or: does not mention, is, is more than, is less than</div></div>'
            '<div class="fld"><label>Words</label><div class="chips">'
            '<span class="tk">price %s</span><span class="tk">discount %s</span><span class="tk">per GB %s</span><span class="tk">$ %s</span>'
            '<span class="add">Add a word</span></div></div>'
            '<div class="addl">%s Add another condition</div></div>'
            '<div class="sec"><h3>Where it goes next</h3>'
            '<div class="br"><span class="bl">Yes</span><span class="to">Legal review <span class="then">then Review</span></span></div>'
            '<div class="br"><span class="bl">Otherwise</span><span class="to">Review</span><span class="lk">%s Always there</span></div>'
            '<div class="addl">%s Add a branch</div>'
            '<div class="note">%s<span>Both ways still pass your approval before Publish. Every path is checked again when you save.</span></div></div>'
            '</aside>' % (ic('split', 20), ic('copy', 16), ic('trash', 16), ic('chev', 16), ic('chev', 16),
                          ic('x', 13), ic('x', 13), ic('x', 13), ic('x', 13), ic('plus', 15), ic('lock', 13), ic('plus', 15), ic('lock', 15)))
    return page('<style>%s</style>' % EF_CSS + rail() + top('design', '<b>Version 3</b><span class="edited">Edited, not saved</span>')
                + palette() + ef_canvas(False) + insp)


def screen_f():
    rows = [('', 'Start', ''), ('', 'Draft copy and Generate image', ''), ('', 'Join', ''),
            ('on', 'Mentions prices?', 'Yes'), ('on', 'Legal review', 'Cleared'), ('miss', 'Your approval is not on this path', ''),
            ('on', 'Schedule', ''), ('on', 'Publish', '')]
    trail = ''.join('<div class="tr %s"><span class="n">%s</span><span>%s</span><span class="o">%s</span></div>'
                    % (c, ic('lock', 12) if c == 'miss' else '', t, o) for c, t, o in rows)
    insp = ('<aside class="insp"><div class="ih"><div class="sic">%s</div><div><div class="t">Legal review</div>'
            '<div class="k">Review step</div></div><span class="grow"></span>'
            '<span class="ibtn b" title="Duplicate">%s</span><span class="ibtn b" title="Remove step">%s</span></div>'
            '<div class="refuse"><div class="ch">%s<div><b>Not saved: this path goes around your approval</b></div></div>'
            '<div class="cb">Publish can only be reached through your approval. Cleared now goes from Legal review straight to Schedule:'
            '<div class="trail"><span class="ln" style="top:15px;height:90px;background:#d4d4d4"></span>'
            '<span class="ln" style="top:105px;height:120px;background:var(--stop)"></span>%s</div></div>'
            '<div class="ca"><span class="btn">Send Cleared to Review instead</span><span class="btn q">Undo this connection</span></div></div>'
            '<div class="sec"><h3>Where it goes next</h3>'
            '<div class="br err"><span class="bl">Cleared</span><span class="to">Schedule</span></div>'
            '<div class="ferr">%s<span>Schedule comes after your approval. Connect Cleared to Review or to Your approval.</span></div>'
            '<div style="height:12px"></div></div>'
            '</aside>' % (ic('eye', 20), ic('copy', 16), ic('trash', 16), ic('alert', 18), trail, ic('alert', 15)))
    return page('<style>%s</style>' % EF_CSS + rail() + top('design', '<b>Version 3</b><span class="edited">Edited, not saved</span>')
                + palette() + ef_canvas(True) + insp)


if __name__ == '__main__':
    for name, fn in [('a-canvas-social-post', screen_a), ('b-step-inspector', screen_b), ('c-run-on-canvas', screen_c),
                     ('d-run-phone', screen_d), ('e-conditions-and-parallel', screen_e), ('f-path-skips-approval', screen_f)]:
        (HERE / (name + '.html')).write_text(fn(), encoding='ascii')
        print('wrote', name + '.html')
