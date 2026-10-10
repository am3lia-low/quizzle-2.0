// Quiz engine: shared by every quiz. The agent never edits this file.
// Reads quiz data from <script id="quiz-data"> and nav data from <script id="nav-data">,
// renders intro -> questions -> result into #app.
// Scoring and tie-break rules must match scripts/quizlib.py exactly.
(function () {
  "use strict";

  var quiz = JSON.parse(document.getElementById("quiz-data").textContent);
  var nav = JSON.parse(document.getElementById("nav-data").textContent);
  var app = document.getElementById("app");
  var outcomeById = {};
  quiz.outcomes.forEach(function (o) { outcomeById[o.id] = o; });

  var answers = []; // chosen answer index per question

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function clear() {
    while (app.firstChild) app.removeChild(app.firstChild);
  }

  function show(screen, name) {
    clear();
    app.dataset.screen = name;
    app.appendChild(screen);
    window.scrollTo(0, 0);
    var focusTarget = screen.querySelector("[data-autofocus]");
    if (focusTarget) focusTarget.focus();
  }

  // ---------- scoring (mirror of quizlib.score) ----------
  function score(picks) {
    var totals = {};
    var lastScored = {};
    quiz.outcomes.forEach(function (o) { totals[o.id] = 0; lastScored[o.id] = -1; });
    picks.forEach(function (answerIndex, q) {
      var scores = quiz.questions[q].answers[answerIndex].scores;
      Object.keys(scores).forEach(function (id) {
        if (scores[id] > 0) {
          totals[id] += scores[id];
          lastScored[id] = q;
        }
      });
    });
    var best = null;
    quiz.outcomes.forEach(function (o) {
      if (best === null) { best = o.id; return; }
      var a = totals[o.id], b = totals[best];
      if (a > b || (a === b && lastScored[o.id] > lastScored[best])) best = o.id;
    });
    return { winner: best, totals: totals };
  }

  // ---------- screens ----------
  function renderIntro() {
    var s = el("section", "screen intro");
    if (quiz.emoji) s.appendChild(el("div", "quiz-emoji", quiz.emoji));
    s.appendChild(el("h1", "quiz-title", quiz.title));
    if (quiz.intro) s.appendChild(el("p", "quiz-intro", quiz.intro));
    s.appendChild(el("p", "quiz-meta", quiz.questions.length + " questions · " + quiz.outcomes.length + " possible results"));
    var start = el("button", "btn btn-primary", quiz.start_label || "Start");
    start.type = "button";
    start.dataset.testid = "start";
    start.setAttribute("data-autofocus", "");
    start.addEventListener("click", function () { answers = []; renderQuestion(0); });
    s.appendChild(start);
    show(s, "intro");
  }

  function renderQuestion(q) {
    var question = quiz.questions[q];
    var s = el("section", "screen question");
    s.dataset.question = String(q);

    var progress = el("div", "progress");
    progress.setAttribute("role", "progressbar");
    progress.setAttribute("aria-valuemin", "0");
    progress.setAttribute("aria-valuemax", String(quiz.questions.length));
    progress.setAttribute("aria-valuenow", String(q));
    var bar = el("div", "progress-bar");
    bar.style.width = (q / quiz.questions.length * 100) + "%";
    progress.appendChild(bar);
    s.appendChild(progress);

    s.appendChild(el("p", "question-count", "Question " + (q + 1) + " of " + quiz.questions.length));
    var heading = el("h2", "question-text", question.text);
    heading.tabIndex = -1;
    heading.setAttribute("data-autofocus", "");
    s.appendChild(heading);

    var list = el("div", "answers");
    question.answers.forEach(function (answer, i) {
      var b = el("button", "answer", answer.text);
      b.type = "button";
      b.dataset.testid = "answer-" + i;
      b.addEventListener("click", function () {
        answers[q] = i;
        answers.length = q + 1;
        if (q + 1 < quiz.questions.length) renderQuestion(q + 1);
        else renderResult();
      });
      list.appendChild(b);
    });
    s.appendChild(list);

    var back = el("button", "btn btn-back", q === 0 ? "← Back to start" : "← Previous question");
    back.type = "button";
    back.dataset.testid = "back";
    back.addEventListener("click", function () {
      if (q === 0) renderIntro(); else renderQuestion(q - 1);
    });
    s.appendChild(back);
    show(s, "question");
  }

  function outcomeCard(o, cls) {
    var card = el("article", cls);
    card.dataset.outcome = o.id;
    if (o.color) card.style.setProperty("--outcome-color", o.color);
    if (o.emoji) card.appendChild(el("div", "result-emoji", o.emoji));
    return card;
  }

  function renderResult() {
    var result = score(answers);
    var o = outcomeById[result.winner];
    var s = el("section", "screen result");
    s.dataset.result = o.id;
    document.body.dataset.result = o.id;

    var card = outcomeCard(o, "result-card");
    card.insertBefore(el("p", "result-label", quiz.result_label || "You got"), card.firstChild);
    var name = el("h2", "result-name", o.name);
    name.tabIndex = -1;
    name.setAttribute("data-autofocus", "");
    card.appendChild(name);
    card.appendChild(el("p", "result-tagline", o.tagline));
    card.appendChild(el("p", "result-description", o.description));
    var traits = el("ul", "result-traits");
    o.traits.forEach(function (t) { traits.appendChild(el("li", null, t)); });
    card.appendChild(traits);

    if (quiz.scoring === "blend") card.appendChild(renderBlend(result.totals));
    s.appendChild(card);

    var actions = el("div", "result-actions");
    var share = el("button", "btn btn-primary", "Share result");
    share.type = "button";
    share.dataset.testid = "share";
    share.addEventListener("click", function () { shareResult(o, share); });
    actions.appendChild(share);
    var again = el("button", "btn", "Take it again");
    again.type = "button";
    again.dataset.testid = "restart";
    again.addEventListener("click", function () { delete document.body.dataset.result; renderIntro(); });
    actions.appendChild(again);
    var allBtn = el("button", "btn", "See all results");
    allBtn.type = "button";
    allBtn.dataset.testid = "all-outcomes";
    actions.appendChild(allBtn);
    s.appendChild(actions);

    var all = el("div", "all-outcomes");
    all.hidden = true;
    quiz.outcomes.forEach(function (x) {
      var mini = outcomeCard(x, "outcome-mini" + (x.id === o.id ? " is-yours" : ""));
      mini.appendChild(el("h3", "outcome-mini-name", x.name));
      mini.appendChild(el("p", "outcome-mini-tagline", x.tagline));
      all.appendChild(mini);
    });
    allBtn.addEventListener("click", function () {
      all.hidden = !all.hidden;
      allBtn.textContent = all.hidden ? "See all results" : "Hide all results";
    });
    s.appendChild(all);
    show(s, "result");
  }

  function renderBlend(totals) {
    var sum = 0;
    Object.keys(totals).forEach(function (id) { sum += totals[id]; });
    var rows = quiz.outcomes
      .filter(function (o) { return totals[o.id] > 0; })
      .sort(function (a, b) { return totals[b.id] - totals[a.id]; })
      .slice(0, 4);
    var box = el("div", "blend");
    box.appendChild(el("p", "blend-label", "Your mix"));
    rows.forEach(function (x) {
      var pct = sum ? Math.round(totals[x.id] / sum * 100) : 0;
      var row = el("div", "blend-row");
      row.dataset.outcome = x.id;
      if (x.color) row.style.setProperty("--outcome-color", x.color);
      row.appendChild(el("span", "blend-name", (x.emoji ? x.emoji + " " : "") + x.name));
      var track = el("span", "blend-bar");
      var fill = el("span", "blend-fill");
      fill.style.width = pct + "%";
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el("span", "blend-pct", pct + "%"));
      box.appendChild(row);
    });
    return box;
  }

  function shareResult(o, button) {
    var url = location.href.split("#")[0];
    var text = "I got " + o.name + (o.emoji ? " " + o.emoji : "") + " on “" + quiz.title + "”";
    function copied() {
      button.textContent = "Link copied!";
      setTimeout(function () { button.textContent = "Share result"; }, 2000);
    }
    if (navigator.share) {
      navigator.share({ title: quiz.title, text: text, url: url }).catch(function () {});
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(text + " " + url).then(copied, function () {});
    }
  }

  // ---------- chrome around the quiz ----------
  function renderNav() {
    var footer = document.getElementById("quiz-nav");
    if (!footer) return;
    function link(href, cls, text) {
      var a = el("a", cls, text);
      a.href = href;
      footer.appendChild(a);
    }
    if (nav.prev) link(nav.prev.href, "nav-prev", "← " + nav.prev.title);
    link(nav.home, "nav-home", "All quizzes");
    if (nav.next) link(nav.next.href, "nav-next", nav.next.title + " →");
  }

  renderNav();
  renderIntro();
})();
