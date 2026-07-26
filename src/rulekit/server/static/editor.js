/* YAML editor decoration for the pack editor: syntax highlighting + live
   syntax linting. No dependencies and no build step — the highlighter is a
   line-oriented tokenizer painted into a <pre> that sits exactly behind the
   real <textarea>, which stays the source of truth (native undo, IME,
   selection and the existing Cmd+S handler all keep working).

   Scope is deliberately SYNTAX ONLY. Pack-schema validation lives in Python
   (lint_overlaps / lint_checks) and stays there — mirroring the schema into
   JS would make two sources of truth that drift. Semantic findings still
   arrive on save, in #lint-box. */

(() => {
  "use strict";

  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;" };
  const esc = (s) => s.replace(/[&<>]/g, (c) => ESC[c]);

  /* ---------- tokenizer ----------

     YAML is line-oriented, so the tokenizer is too. The only cross-line state
     we must carry is block scalars (`|` / `>`), whose bodies are opaque text
     and must not be parsed as mappings — packs use them for message strings. */

  const RE_INDENT = /^[ \t]*/;
  const RE_DOC_MARKER = /^(---|\.\.\.)\s*$/;
  const RE_KEY = /^(?:"(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^:#\n]*?)\s*:(?=\s|$)/;
  const RE_NUM = /^-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?\b/;
  const RE_CONST = /^(?:true|false|yes|no|on|off|null|~)\b/i;
  const RE_ANCHOR = /^[&*][\w-]+/;
  const RE_TAG = /^!{1,2}[\w:/.-]*/;

  function tokenizeValue(text, out) {
    let i = 0;
    while (i < text.length) {
      const rest = text.slice(i);
      const ch = rest[0];

      if (ch === " " || ch === "\t") {
        const ws = rest.match(/^[ \t]+/)[0];
        // a `#` only opens a comment when preceded by whitespace
        out.push(["", ws]);
        i += ws.length;
        continue;
      }
      if (ch === "#") {
        out.push(["tok-comment", rest]);
        return;
      }
      if (ch === '"' || ch === "'") {
        const m = ch === '"'
          ? rest.match(/^"(?:[^"\\]|\\.)*"?/)
          : rest.match(/^'(?:[^']|'')*'?/);
        out.push(["tok-str", m[0]]);
        i += m[0].length;
        continue;
      }
      let m;
      if ((m = rest.match(RE_ANCHOR))) { out.push(["tok-anchor", m[0]]); i += m[0].length; continue; }
      if ((m = rest.match(RE_TAG)))    { out.push(["tok-tag", m[0]]);    i += m[0].length; continue; }
      if ((m = rest.match(RE_NUM)))    { out.push(["tok-num", m[0]]);    i += m[0].length; continue; }
      if ((m = rest.match(RE_CONST)))  { out.push(["tok-bool", m[0]]);   i += m[0].length; continue; }
      if ("{}[],".includes(ch))        { out.push(["tok-punct", ch]);    i += 1; continue; }

      // inside a flow collection a nested `key:` still reads as a key
      if ((m = rest.match(/^[\w.\/-]+(?=\s*:(?:\s|$))/))) {
        out.push(["tok-key", m[0]]);
        i += m[0].length;
        continue;
      }
      if (ch === ":") { out.push(["tok-punct", ch]); i += 1; continue; }

      // plain scalar: run to the next structural character
      m = rest.match(/^[^\s{}\[\],:#]+/) || [ch];
      out.push(["tok-plain", m[0]]);
      i += m[0].length;
    }
  }

  function tokenizeLine(line, st) {
    const out = [];

    // inside an open block scalar: opaque text until the indent drops back
    if (st.blockIndent !== null) {
      const indent = line.match(RE_INDENT)[0].length;
      if (line.trim() === "" || indent > st.blockIndent) {
        out.push(["tok-str", line]);
        return out;
      }
      st.blockIndent = null;
    }

    const ws = line.match(RE_INDENT)[0];
    let rest = line.slice(ws.length);
    if (ws) out.push(["", ws]);

    if (rest === "") return out;
    if (rest.startsWith("#")) { out.push(["tok-comment", rest]); return out; }
    if (RE_DOC_MARKER.test(rest)) { out.push(["tok-doc", rest]); return out; }

    // one or more list dashes may open the line: "- - foo"
    while (rest.startsWith("- ") || rest === "-") {
      out.push(["tok-dash", "-"]);
      rest = rest.slice(1);
      const gap = rest.match(RE_INDENT)[0];
      if (gap) out.push(["", gap]);
      rest = rest.slice(gap.length);
    }

    const km = rest.match(RE_KEY);
    if (km) {
      const key = km[0].slice(0, km[0].lastIndexOf(":"));
      out.push(["tok-key", key]);
      out.push(["tok-punct", ":"]);
      rest = rest.slice(km[0].length);
      // a block scalar header opens a body we must not parse
      const bm = rest.match(/^\s*([|>])([+-]?\d*)\s*$/);
      if (bm) {
        out.push(["tok-block", rest]);
        st.blockIndent = ws.length;
        return out;
      }
    }
    tokenizeValue(rest, out);
    return out;
  }

  function highlight(text) {
    const st = { blockIndent: null };
    return text.split("\n").map((line) => {
      const toks = tokenizeLine(line, st);
      // a trailing \n in a <pre> is swallowed, so empty lines need a filler
      if (!toks.length) return "\u200b";
      return toks
        .map(([cls, s]) => (cls ? `<span class="${cls}">${esc(s)}</span>` : esc(s)))
        .join("");
    }).join("\n");
  }

  /* ---------- linter ----------

     Every rule below fires only when it is CERTAIN the YAML is wrong. A false
     squiggle on valid pack source is worse than a missed one: it trains you to
     ignore the gutter. Anything ambiguous is left to the Python validator on
     save. Returns [{line (1-based), level, code, message}]. */

  /* Index just past the quote that closes the one opening at 0, or -1 if the
     line never closes it. Only ever called when the value STARTS with a quote:
     scanning arbitrary text for quotes would flag the apostrophe in a plain
     scalar like `note: don't do this`. */
  function closeQuoteEnd(val) {
    const q = val[0];
    let i = 1;
    while (i < val.length) {
      if (q === '"' && val[i] === "\\") { i += 2; continue; }
      if (val[i] === q) {
        if (q === "'" && val[i + 1] === "'") { i += 2; continue; }  // '' escape
        return i + 1;
      }
      i++;
    }
    return -1;
  }

  function lint(text) {
    const problems = [];
    const lines = text.split("\n");
    const add = (line, level, code, message) =>
      problems.push({ line: line + 1, level, code, message });

    const indents = [0];          // open indentation levels
    const keysAt = new Map();     // indent -> Set of keys seen in this mapping
    let flowDepth = 0;            // inside {...} / [...] structure is free-form
    let blockIndent = null;

    lines.forEach((raw, n) => {
      const ws = raw.match(RE_INDENT)[0];
      const indent = ws.length;
      const body = raw.slice(indent);

      // block scalar bodies are opaque text, not structure
      if (blockIndent !== null) {
        if (body === "" || indent > blockIndent) return;
        blockIndent = null;
      }
      if (body === "" || body.startsWith("#")) return;

      // --- tabs in indentation: YAML forbids them outright
      if (ws.includes("\t")) {
        add(n, "error", "tab-indent",
            "tab character in indentation — YAML forbids tabs for indenting");
        return; // column maths below would be meaningless
      }

      if (flowDepth === 0 && !RE_DOC_MARKER.test(body)) {
        // --- indentation must return to a level that was actually opened
        if (indent > indents[indents.length - 1]) {
          indents.push(indent);
        } else {
          while (indents.length > 1 && indents[indents.length - 1] > indent) {
            indents.pop();
            for (const k of [...keysAt.keys()]) if (k > indent) keysAt.delete(k);
          }
          if (indents[indents.length - 1] !== indent) {
            add(n, "error", "bad-indent",
                `indent ${indent} matches no open block (expected ` +
                `${indents[indents.length - 1]})`);
          }
        }

        // --- duplicate keys silently overwrite in PyYAML: a real pack hazard
        let keyIndent = indent;
        let rest = body;
        while (rest.startsWith("- ") || rest === "-") {
          // each dash opens a fresh mapping, so its key set starts empty
          rest = rest.slice(1).replace(RE_INDENT, "");
          keyIndent = indent + (body.length - rest.length);
          keysAt.delete(keyIndent);
        }
        /* NOT SHIPPED — the "orphan indent" rule. A key with a scalar value
           cannot have children, so this is invalid YAML:

               one: 1
                two: 2        <- nothing may nest under `one: 1`

           It is the one common mistake the rules above miss (a deeper indent
           always looks like a legal new block). It is unshipped because a
           legal multi-line PLAIN scalar is textually identical:

               note: this is a long
                 continuation line   <- valid YAML, would be flagged

           Whether that shape ever appears in a pack is a judgment about this
           corpus, not about YAML. A naive prototype fired 286 times on the
           current packs; most were a dash-stripping bug, but the plain-scalar
           hazard survives any fix. Implement here if you want it — the loop
           already has `indent`, and `prevIndent` / `prevHadValue` would need
           threading through from the previous iteration. */

        // A line that opens a flow collection is not a block mapping entry:
        // `- {lit: "'s"}` would otherwise read as key `{lit` with the value
        // running to `}`. Flow interiors are left to the Python validator.
        const isFlow = rest.startsWith("{") || rest.startsWith("[");
        const km = isFlow ? null : rest.match(RE_KEY);
        if (km) {
          const key = km[0].slice(0, km[0].lastIndexOf(":")).trim();
          if (!keysAt.has(keyIndent)) keysAt.set(keyIndent, new Set());
          const seen = keysAt.get(keyIndent);
          if (seen.has(key)) {
            add(n, "error", "duplicate-key",
                `duplicate key '${key}' — the later value silently wins`);
          }
          seen.add(key);

          // --- a value opening with a quote must close on the same line
          const val = rest.slice(km[0].length).trim();
          const q = val[0];
          if (q === '"' || q === "'") {
            const end = closeQuoteEnd(val);
            if (end < 0) {
              add(n, "error", "unclosed-quote",
                  `unterminated ${q === '"' ? "double" : "single"}-quoted string`);
            } else if (!/[{}[\],]/.test(val)) {
              // outside flow context nothing may follow the closing quote but
              // whitespace or a comment; inside it, `, b: 2}` is legal so skip
              const tail = val.slice(end);
              if (tail.trim() && !tail.trimStart().startsWith("#")) {
                add(n, "error", "quote-trailing",
                    "unexpected text after the closing quote");
              }
            }
          }
          if (/^\s*[|>][+-]?\d*\s*$/.test(rest.slice(km[0].length))) {
            blockIndent = indent;
          }
        }
      }

      // track flow depth last so a line opening `{` still lints as structure
      for (const ch of body.replace(/#.*$/, "")) {
        if (ch === "{" || ch === "[") flowDepth++;
        else if (ch === "}" || ch === "]") flowDepth = Math.max(0, flowDepth - 1);
      }
    });

    if (flowDepth > 0) {
      add(lines.length - 1, "error", "unclosed-flow",
          "unclosed { or [ — flow collection never terminates");
    }
    return problems;
  }

  /* ---------- mount ---------- */

  const ta = document.getElementById("editor");
  if (!ta) return;

  const wrap = document.createElement("div");
  wrap.id = "editor-wrap";
  const gutter = document.createElement("div");
  gutter.id = "editor-gutter";
  const scroller = document.createElement("div");
  scroller.id = "editor-scroll";
  const pre = document.createElement("pre");
  pre.id = "editor-highlight";
  pre.setAttribute("aria-hidden", "true");

  ta.parentNode.insertBefore(wrap, ta);
  scroller.append(pre, ta);
  wrap.append(gutter, scroller);

  let problems = [];

  function renderGutter() {
    const byLine = new Map();
    for (const p of problems) if (!byLine.has(p.line)) byLine.set(p.line, p);
    const count = ta.value.split("\n").length;
    const rows = [];
    for (let i = 1; i <= count; i++) {
      const p = byLine.get(i);
      rows.push(
        p
          ? `<div class="gl ${p.level}" data-line="${i}" title="${esc(p.code)}: ${esc(p.message)}">${i}</div>`
          : `<div class="gl" data-line="${i}">${i}</div>`
      );
    }
    gutter.innerHTML = rows.join("");
  }

  function renderProblems() {
    const box = document.getElementById("editor-problems");
    if (!box) return;
    box.replaceChildren();
    box.classList.toggle("hidden", problems.length === 0);
    for (const p of problems) {
      const row = document.createElement("div");
      row.className = `lint-item ${p.level}`;
      row.textContent = `line ${p.line} · [${p.code}] ${p.message}`;
      row.onclick = () => gotoLine(p.line);
      box.append(row);
    }
  }

  function gotoLine(line) {
    const lines = ta.value.split("\n");
    let pos = 0;
    for (let i = 0; i < line - 1 && i < lines.length; i++) pos += lines[i].length + 1;
    ta.focus();
    ta.setSelectionRange(pos, pos + (lines[line - 1] || "").length);
    // put the target line roughly a third down the viewport
    const lh = parseFloat(getComputedStyle(ta).lineHeight) || 16;
    ta.scrollTop = Math.max(0, (line - 1) * lh - ta.clientHeight / 3);
    sync();
  }

  function sync() {
    pre.scrollTop = ta.scrollTop;
    pre.scrollLeft = ta.scrollLeft;
    gutter.scrollTop = ta.scrollTop;
  }

  let pending = null;
  function refresh() {
    pre.innerHTML = highlight(ta.value);
    problems = lint(ta.value);
    renderGutter();
    renderProblems();
    sync();
    const badge = document.getElementById("editor-syntax");
    if (badge) {
      const errs = problems.filter((p) => p.level === "error").length;
      badge.textContent = errs ? `${errs} syntax error${errs > 1 ? "s" : ""}` : "";
      badge.style.color = "var(--red)";
    }
  }

  function schedule() {
    if (pending) cancelAnimationFrame(pending);
    pending = requestAnimationFrame(() => { pending = null; refresh(); });
  }

  ta.addEventListener("input", schedule);
  ta.addEventListener("scroll", sync);

  // Tab indents instead of leaving the field — YAML editing needs it, and the
  // linter above treats a literal tab as an error, so insert spaces.
  ta.addEventListener("keydown", (e) => {
    if (e.key !== "Tab" || e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault();
    const { selectionStart: s, selectionEnd: t, value: v } = ta;
    if (e.shiftKey) {
      const bol = v.lastIndexOf("\n", s - 1) + 1;
      const strip = v.slice(bol, bol + 2) === "  " ? 2 : (v[bol] === " " ? 1 : 0);
      if (!strip) return;
      ta.value = v.slice(0, bol) + v.slice(bol + strip);
      ta.setSelectionRange(s - strip, t - strip);
    } else {
      ta.value = v.slice(0, s) + "  " + v.slice(t);
      ta.setSelectionRange(s + 2, s + 2);
    }
    schedule();
  });

  window.RulekitEditor = {
    refresh,
    lint,
    highlight,
    gotoLine,
    problems: () => problems,
  };
})();
