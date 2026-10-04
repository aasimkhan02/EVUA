import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import heroImage from '../../assets/hero.png';
import './landing.css';

const Landing = () => {
  const navigate = useNavigate();
  const [activeDiffTab, setActiveDiffTab] = useState('angular');
  const [copied, setCopied] = useState(false);

  const copyCliCommand = () => {
    navigator.clipboard.writeText('npx @evua/cli scan ./legacy-app');
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const diffData = {
    angular: {
      title: 'user-directory.controller.js → user-directory.component.ts',
      legacyName: 'Source Code (Legacy AngularJS 1.5)',
      modernName: 'Transformed Output (Angular 18 Standalone)',
      badge: 'Strict Signals & Typed',
      ruleText: 'Transformation Rule #409: Replaced AngularJS $scope digest cycles with zero-overhead Angular 18 reactive Signals.',
      legacyCode: (
        <>
          <span className="text-slate-500">01</span>  angular.module('app')<br/>
          <span className="text-slate-500">02</span>    .controller('UserCtrl', function($scope, $http) &#123;<br/>
          <span className="text-slate-500">03</span>      $scope.users = [];<br/>
          <span className="text-slate-500">04</span>      $scope.loading = true;<br/>
          <span className="text-slate-500">05</span>      <br/>
          <span className="text-slate-500">06</span>      <span className="text-rose-300 bg-rose-950/40 px-1">// Untyped promise with scope leakage</span><br/>
          <span className="text-slate-500">07</span>      $scope.loadUsers = function() &#123;<br/>
          <span className="text-slate-500">08</span>        $http.get('/api/v1/users')<br/>
          <span className="text-slate-500">09</span>          .then(function(res) &#123;<br/>
          <span className="text-slate-500">10</span>            $scope.users = res.data;<br/>
          <span className="text-slate-500">11</span>            $scope.loading = false;<br/>
          <span className="text-slate-500">12</span>            $scope.$applyAsync();<br/>
          <span className="text-slate-500">13</span>          &#125;);<br/>
          <span className="text-slate-500">14</span>      &#125;;<br/>
          <span className="text-slate-500">15</span>      <br/>
          <span className="text-slate-500">16</span>      $scope.loadUsers();<br/>
          <span className="text-slate-500">17</span>    &#125;);
        </>
      ),
      modernCode: (
        <>
          <span className="text-slate-500">01</span>  <span className="text-purple-400">import</span> &#123; Component, inject, signal &#125; <span className="text-purple-400">from</span> <span className="text-emerald-300">'@angular/core'</span>;<br/>
          <span className="text-slate-500">02</span>  <span className="text-purple-400">import</span> &#123; HttpClient &#125; <span className="text-purple-400">from</span> <span className="text-emerald-300">'@angular/common/http'</span>;<br/>
          <span className="text-slate-500">03</span>  <span className="text-purple-400">import</span> &#123; User &#125; <span className="text-purple-400">from</span> <span className="text-emerald-300">'./user.model'</span>;<br/>
          <span className="text-slate-500">04</span>  <br/>
          <span className="text-slate-500">05</span>  <span className="text-purple-400">@Component</span>(&#123;<br/>
          <span className="text-slate-500">06</span>    selector: <span className="text-emerald-300">'app-user-directory'</span>,<br/>
          <span className="text-slate-500">07</span>    standalone: <span className="text-sky-300">true</span>,<br/>
          <span className="text-slate-500">08</span>    templateUrl: <span className="text-emerald-300">'./user-directory.html'</span><br/>
          <span className="text-slate-500">09</span>  &#125;)<br/>
          <span className="text-slate-500">10</span>  <span className="text-purple-400">export class</span> <span className="text-sky-300">UserDirectoryComponent</span> &#123;<br/>
          <span className="text-slate-500">11</span>    <span className="text-purple-400">private readonly</span> http = inject(HttpClient);<br/>
          <span className="text-slate-500">12</span>    <span className="text-emerald-300 bg-emerald-950/40 px-1">readonly users = signal&lt;User[]&gt;([]);</span><br/>
          <span className="text-slate-500">13</span>    <span className="text-emerald-300 bg-emerald-950/40 px-1">readonly isLoading = signal&lt;boolean&gt;(false);</span><br/>
          <span className="text-slate-500">14</span>  <br/>
          <span className="text-slate-500">15</span>    constructor() &#123; <span className="text-purple-400">this</span>.loadUsers(); &#125;<br/>
          <span className="text-slate-500">16</span>  <br/>
          <span className="text-slate-500">17</span>    <span className="text-purple-400">async</span> loadUsers(): Promise&lt;<span className="text-sky-300">void</span>&gt; &#123;<br/>
          <span className="text-slate-500">18</span>      <span className="text-purple-400">const</span> data = <span className="text-purple-400">await</span> <span className="text-purple-400">this</span>.http.get&lt;User[]&gt;(<span className="text-emerald-300">'/api/v1/users'</span>).toPromise();<br/>
          <span className="text-slate-500">19</span>      <span className="text-purple-400">this</span>.users.set(data ?? []);<br/>
          <span className="text-slate-500">20</span>    &#125;<br/>
          <span className="text-slate-500">21</span>  &#125;
        </>
      )
    },
    php: {
      title: 'db-connection.php → DatabaseClient.php (PHP 8.3 PDO)',
      legacyName: 'Source Code (PHP 5.6 mysql_*)',
      modernName: 'Transformed Output (PHP 8.3 Strict PDO)',
      badge: 'Type Safe & Injection Free',
      ruleText: 'Transformation Rule #182: Migrated deprecated mysql_* procedural queries to parameterized PDO with strict return types.',
      legacyCode: (
        <>
          <span className="text-slate-500">01</span>  <span className="text-primary">&lt;?php</span><br/>
          <span className="text-slate-500">02</span>  <span className="text-rose-300 bg-rose-950/40 px-1">// Deprecated mysql_connect with potential SQL injection</span><br/>
          <span className="text-slate-500">03</span>  $conn = mysql_connect('localhost', 'root', 'pass');<br/>
          <span className="text-slate-500">04</span>  mysql_select_db('enterprise_db', $conn);<br/>
          <span className="text-slate-500">05</span>  <br/>
          <span className="text-slate-500">06</span>  function getUsers($role) &#123;<br/>
          <span className="text-slate-500">07</span>    $query = "SELECT * FROM users WHERE role = '$role'";<br/>
          <span className="text-slate-500">08</span>    $res = mysql_query($query);<br/>
          <span className="text-slate-500">09</span>    $rows = array();<br/>
          <span className="text-slate-500">10</span>    while($r = mysql_fetch_assoc($res)) &#123;<br/>
          <span className="text-slate-500">11</span>      $rows[] = $r;<br/>
          <span className="text-slate-500">12</span>    &#125;<br/>
          <span className="text-slate-500">13</span>    return $rows;<br/>
          <span className="text-slate-500">14</span>  &#125;
        </>
      ),
      modernCode: (
        <>
          <span className="text-slate-500">01</span>  <span className="text-primary font-bold">&lt;?php</span><br/>
          <span className="text-slate-500">02</span>  <span className="text-purple-400">declare</span>(strict_types=1);<br/>
          <span className="text-slate-500">03</span>  <br/>
          <span className="text-slate-500">04</span>  <span className="text-purple-400">namespace</span> App\Infrastructure\Database;<br/>
          <span className="text-slate-500">05</span>  <span className="text-purple-400">use</span> PDO, PDOStatement;<br/>
          <span className="text-slate-500">06</span>  <br/>
          <span className="text-slate-500">07</span>  <span className="text-purple-400">final readonly class</span> <span className="text-sky-300">UserRepository</span> &#123;<br/>
          <span className="text-slate-500">08</span>    <span className="text-purple-400">public function</span> __construct(<br/>
          <span className="text-slate-500">09</span>      <span className="text-purple-400">private</span> PDO $pdo<br/>
          <span className="text-slate-500">10</span>    ) &#123;&#125;<br/>
          <span className="text-slate-500">11</span>  <br/>
          <span className="text-slate-500">12</span>    <span className="text-purple-400">public function</span> getUsersByRole(<span className="text-sky-300">string</span> $role): <span className="text-yellow-300">array</span> &#123;<br/>
          <span className="text-slate-500">13</span>      $stmt = $this-&gt;pdo-&gt;prepare(<span className="text-emerald-300">'SELECT id, name, email FROM users WHERE role = :role'</span>);<br/>
          <span className="text-slate-500">14</span>      $stmt-&gt;execute([<span className="text-emerald-300">'role'</span> =&gt; $role]);<br/>
          <span className="text-slate-500">15</span>      <span className="text-purple-400">return</span> $stmt-&gt;fetchAll(PDO::FETCH_CLASS, UserDTO::class);<br/>
          <span className="text-slate-500">16</span>    &#125;<br/>
          <span className="text-slate-500">17</span>  &#125;
        </>
      )
    },
    vue: {
      title: 'CartView.vue (Vue 2 Options) → CartView.vue (Vue 3 script setup)',
      legacyName: 'Source Code (Vue 2 Options API)',
      modernName: 'Transformed Output (Vue 3 <script setup>)',
      badge: 'Composition API & TS',
      ruleText: 'Transformation Rule #311: Converted Vue 2 Options state/computed/methods to Vue 3 ref/computed with TypeScript script setup.',
      legacyCode: (
        <>
          <span className="text-slate-500">01</span>  &lt;script&gt;<br/>
          <span className="text-slate-500">02</span>  export default &#123;<br/>
          <span className="text-slate-500">03</span>    data() &#123;<br/>
          <span className="text-slate-500">04</span>      return &#123; items: [], coupon: '' &#125;;<br/>
          <span className="text-slate-500">05</span>    &#125;,<br/>
          <span className="text-slate-500">06</span>    computed: &#123;<br/>
          <span className="text-slate-500">07</span>      total() &#123;<br/>
          <span className="text-slate-500">08</span>        return this.items.reduce((acc, i) =&gt; acc + i.price, 0);<br/>
          <span className="text-slate-500">09</span>      &#125;<br/>
          <span className="text-slate-500">10</span>    &#125;,<br/>
          <span className="text-slate-500">11</span>    methods: &#123;<br/>
          <span className="text-slate-500">12</span>      checkout() &#123; this.$router.push('/pay'); &#125;<br/>
          <span className="text-slate-500">13</span>    &#125;<br/>
          <span className="text-slate-500">14</span>  &#125;<br/>
          <span className="text-slate-500">15</span>  &lt;/script&gt;
        </>
      ),
      modernCode: (
        <>
          <span className="text-slate-500">01</span>  &lt;script setup lang="ts"&gt;<br/>
          <span className="text-slate-500">02</span>  <span className="text-purple-400">import</span> &#123; ref, computed &#125; <span className="text-purple-400">from</span> <span className="text-emerald-300">'vue'</span>;<br/>
          <span className="text-slate-500">03</span>  <span className="text-purple-400">import</span> &#123; useRouter &#125; <span className="text-purple-400">from</span> <span className="text-emerald-300">'vue-router'</span>;<br/>
          <span className="text-slate-500">04</span>  <span className="text-purple-400">import type</span> &#123; CartItem &#125; <span className="text-purple-400">from</span> <span className="text-emerald-300">'@/types'</span>;<br/>
          <span className="text-slate-500">05</span>  <br/>
          <span className="text-slate-500">06</span>  <span className="text-purple-400">const</span> router = useRouter();<br/>
          <span className="text-slate-500">07</span>  <span className="text-emerald-300 bg-emerald-950/40 px-1">const items = ref&lt;CartItem[]&gt;([]);</span><br/>
          <span className="text-slate-500">08</span>  <span className="text-emerald-300 bg-emerald-950/40 px-1">const coupon = ref&lt;string&gt;('');</span><br/>
          <span className="text-slate-500">09</span>  <br/>
          <span className="text-slate-500">10</span>  <span className="text-purple-400">const</span> total = computed(() =&gt; items.value.reduce((acc, i) =&gt; acc + i.price, 0));<br/>
          <span className="text-slate-500">11</span>  <span className="text-purple-400">const</span> checkout = () =&gt; router.push('/pay');<br/>
          <span className="text-slate-500">12</span>  &lt;/script&gt;
        </>
      )
    }
  };

  const currentDiff = diffData[activeDiffTab];

  return (
    <div className="landing-page min-h-screen bg-[#FCFDFD] font-body-md text-on-surface relative selection:bg-primary/20 selection:text-primary">
      {/* Ambient Grid Pattern and Glow */}
      <div className="fixed inset-0 pointer-events-none bg-grid-pattern opacity-30 z-0" />
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[900px] h-[350px] bg-gradient-to-b from-primary/10 via-secondary-container/10 to-transparent blur-[80px] pointer-events-none z-0" />

      {/* Header */}
      <header className="fixed top-0 left-0 w-full z-50 bg-[#FCFDFD]/85 backdrop-blur-2xl">
        <div className="h-16 max-w-[1440px] mx-auto px-6 md:px-12 flex items-center justify-between gap-6">
          <div className="flex items-center gap-14">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="flex items-center gap-1 scale-110">
                <span className="w-1.5 h-5 rounded-full bg-primary -skew-x-12 group-hover:scale-y-110 transition-transform" />
                <span className="w-1.5 h-6 rounded-full bg-primary-container -skew-x-12 group-hover:scale-y-110 transition-transform delay-75" />
                <span className="w-1.5 h-4 rounded-full bg-secondary-container -skew-x-12 group-hover:scale-y-110 transition-transform delay-150" />
              </div>
              <span className="font-headline-sm font-bold tracking-tight text-on-surface text-[1.5rem]">EVUA</span>
            </Link>
            <nav className="hidden lg:flex items-center gap-6 text-sm">
              <a href="#hero" className="transition-colors text-primary font-semibold">Product</a>
              <a href="#how-it-works" className="text-on-surface-variant hover:text-on-surface transition-colors font-medium">How it works</a>
              <a href="#diff-lab" className="text-on-surface-variant hover:text-on-surface transition-colors font-medium">Integration</a>
              <a href="#stacks" className="text-on-surface-variant hover:text-on-surface transition-colors font-medium">Documentation</a>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1.5 hover:bg-surface-container-high transition-colors text-on-surface text-sm font-mono"
            >
              <svg
                className="w-[22px] h-[22px]"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M12 2C6.48 2 2 6.58 2 12.22c0 4.52 2.87 8.35 6.84 9.7.5.1.68-.22.68-.48v-1.7c-2.78.62-3.37-1.37-3.37-1.37-.46-1.2-1.11-1.52-1.11-1.52-.91-.64.07-.63.07-.63 1 .08 1.53 1.05 1.53 1.05.9 1.58 2.35 1.12 2.92.86.09-.67.35-1.12.64-1.38-2.22-.26-4.55-1.14-4.55-5.07 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.7 0 0 .84-.28 2.75 1.05A9.3 9.3 0 0 1 12 7.98c.85 0 1.7.12 2.5.36 1.9-1.33 2.74-1.05 2.74-1.05.55 1.4.2 2.44.1 2.7.64.72 1.03 1.63 1.03 2.75 0 3.94-2.34 4.8-4.57 5.06.36.32.68.94.68 1.9v2.82c0 .27.18.59.69.48A10.23 10.23 0 0 0 22 12.22C22 6.58 17.52 2 12 2Z" />
              </svg>
              <span className="font-lg">GitHub</span>
            </a>
            <Link
              to="/project/123"
              className="inline-flex items-center gap-1.5 px-5 py-3 rounded-lg bg-black hover:bg-primary text-white hover:text-on-primary transition-all text-xs font-semibold shadow-sm group"            >
              <span>Start a Migration</span>
              <span className="material-symbols-outlined text-[16px] group-hover:translate-x-0.5 transition-transform">arrow_forward</span>
            </Link>
            <Link
              to="/history"
              title="Migration History"
              className="w-8 h-8 rounded-full bg-primary hover:bg-primary/90 flex items-center justify-center shrink-0 text-white shadow-sm transition-transform active:scale-95"
            >
              <span className="material-symbols-outlined text-[18px]">history</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="w-full relative z-10">
        {/* ========================================== */}
        {/* 1. HERO FRAME (hero.png as background)     */}
        {/* ========================================== */}
        <section id="hero" className="hero-frame-section relative w-full border-b border-surface-container-highest/40 overflow-hidden">
          {/* Hero Background Image */}
          <div
            className="hero-frame-bg"
            style={{ backgroundImage: `url(${heroImage})` }}
          />

          {/* Atmospheric Ambient Glows */}
          <div className="hero-glow-1" />
          <div className="hero-glow-2" />

          {/* Hero Content Stage */}
          <div className="relative z-10 w-full max-w-[1440px] mx-auto px-6 md:px-12 pt-24 pb-14 lg:pt-28 lg:pb-16">
            <div className="max-w-2xl flex flex-col gap-5">
              {/* Legacy -> Modern Badge */}
              <div className="inline-flex items-center gap-2 self-start px-0 py-1.5 text-on-surface-variant font-mono text-xs uppercase tracking-[0.2em]">
                <span className="w-2 h-2 rounded-full bg-primary animate-ping" />
                <span>Legacy</span>
                <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                <span className="text-primary font-bold">Modern</span>
              </div>

              {/* Giant Headline */}
              <div className="flex flex-col">
                <h1 className="
                  font-display
                  text-[10vh]
                  lg:text-[26vh]
                  leading-[0.92]
                  tracking-tight
                  font-extrabold
                  mb-2
                  bg-gradient-to-r
                  from-[#172033] from-[0%]
                  via-[#2E8CC4] via-[28%]
                  to-[#63D5F7] to-[75%]
                  bg-clip-text
                  text-transparent
                ">
                  EVUA
                </h1>
                <h2 className="font-headline-xl text-headline-xl lg:text-[2.75rem] leading-[1.08] tracking-tight font-bold text-on-surface">
                  UPGRADE WHAT <br />
                  YOU <span className="bg-gradient-to-r from-primary via-primary-container to-secondary-container bg-clip-text text-transparent">ALREADY HAVE.</span>
                </h2>
              </div>

              {/* Subheading */}
              <p className="font-body-lg text-body-lg text-on-surface-variant max-w-md leading-relaxed">
                Automated, AI-assisted migration of legacy AngularJS, PHP, Vue 2, and backend applications to modern, maintainable codebases without regressions.
              </p>

              {/* CTAs */}
              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Link
                  to="/project/123"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-lg bg-black text-white transition-all duration-300 font-semibold shadow-lg group"                >
                  <span>Start a Migration</span>
                  <span className="material-symbols-outlined text-[18px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
                </Link>
                <a
                  href="#how-it-works"
                  className="inline-flex items-center gap-2 px-5 py-3.5 rounded-full bg-surface-container hover:bg-surface-container-highest text-on-surface transition-colors font-semibold shadow-sm"
                >
                  <span className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                    <span className="material-symbols-outlined text-[16px] translate-x-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>play_arrow</span>
                  </span>
                  <span>See how it works</span>
                </a>
              </div>

              {/* Feature Attribute Badges Grid */}
              <div className="grid grid-cols-2 gap-2.5 pt-3 max-w-lg">
                <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-surface-container-low/90 backdrop-blur-md border border-surface-container-high/80 shadow-sm">
                  <span className="w-7 h-7 rounded-lg bg-tertiary-fixed/30 text-tertiary flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[16px]">account_tree</span>
                  </span>
                  <span className="text-xs font-medium text-on-surface leading-tight">AST Transformations</span>
                </div>
                <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-surface-container-low/90 backdrop-blur-md border border-surface-container-high/80 shadow-sm">
                  <span className="w-7 h-7 rounded-lg bg-secondary-fixed/40 text-secondary flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[16px]">verified</span>
                  </span>
                  <span className="text-xs font-medium text-on-surface leading-tight">AI Verification</span>
                </div>
                <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-surface-container-low/90 backdrop-blur-md border border-surface-container-high/80 shadow-sm">
                  <span className="w-7 h-7 rounded-lg bg-primary-fixed/40 text-primary flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[16px]">compare</span>
                  </span>
                  <span className="text-xs font-medium text-on-surface leading-tight">Side-by-side Review</span>
                </div>
                <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-surface-container-low/90 backdrop-blur-md border border-surface-container-high/80 shadow-sm">
                  <span className="w-7 h-7 rounded-lg bg-tertiary-fixed/30 text-tertiary flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[16px]">history</span>
                  </span>
                  <span className="text-xs font-medium text-on-surface leading-tight">Git-based Rollback</span>
                </div>
              </div>

              {/* Supported Stacks Mini Bar */}
              <div className="pt-2">
                <span className="font-mono text-xs text-outline uppercase tracking-wider block mb-2 font-semibold">Supported Stacks</span>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container text-xs text-on-surface font-mono border border-surface-container-high">
                    <span className="w-4 h-4 rounded bg-red-600 text-white flex items-center justify-center text-[10px] font-black">A</span>
                    <span>AngularJS → Angular 18+</span>
                  </div>
                  <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container text-xs text-on-surface font-mono border border-surface-container-high">
                    <span className="w-4 h-4 rounded bg-indigo-600 text-white flex items-center justify-center text-[10px] font-black">P</span>
                    <span>PHP 5.6+ → PHP 8.x+</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* 2. LOGO / ENTERPRISE TRUST STRIP           */}
        {/* ========================================== */}
        <section className="w-full bg-surface-container-low py-10 border-y border-surface-container-highest/60">
          <div className="max-w-[1440px] mx-auto px-6 md:px-12 flex flex-col items-center gap-6">
            <p className="font-mono text-xs uppercase tracking-wider text-outline text-center font-semibold">
              Trusted by engineering leaders refactoring millions of legacy lines
            </p>
            <div className="w-full grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 items-center justify-items-center opacity-75">
              <div className="flex items-center gap-2 font-bold tracking-tighter text-on-surface-variant">
                <span className="material-symbols-outlined text-primary text-[22px]">account_balance</span>
                <span>APEX FIN</span>
              </div>
              <div className="flex items-center gap-2 font-bold tracking-tighter text-on-surface-variant">
                <span className="material-symbols-outlined text-secondary text-[22px]">vital_signs</span>
                <span>SYNAPSE MED</span>
              </div>
              <div className="flex items-center gap-2 font-bold tracking-tighter text-on-surface-variant">
                <span className="material-symbols-outlined text-primary-container text-[22px]">cloud_sync</span>
                <span>STRATA CLOUD</span>
              </div>
              <div className="flex items-center gap-2 font-bold tracking-tighter text-on-surface-variant">
                <span className="material-symbols-outlined text-on-surface text-[22px]">hub</span>
                <span>VECTOR CORP</span>
              </div>
              <div className="flex items-center gap-2 font-bold tracking-tighter text-on-surface-variant">
                <span className="material-symbols-outlined text-tertiary text-[22px]">shield</span>
                <span>AURA DEFENSE</span>
              </div>
              <div className="flex items-center gap-2 font-bold tracking-tighter text-on-surface-variant">
                <span className="material-symbols-outlined text-primary text-[22px]">local_mall</span>
                <span>OMNI RETAIL</span>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* 3. HOW IT WORKS / 4-STEP REFACTOR PIPELINE  */}
        {/* ========================================== */}
        <section id="how-it-works" className="w-full max-w-[1440px] mx-auto px-6 md:px-12 py-24">
          <div className="flex flex-col items-center text-center mb-16">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-fixed text-on-primary-fixed-variant font-mono text-xs uppercase tracking-wider mb-3 font-semibold">
              Architecture Pipeline
            </div>
            <h2 className="font-headline-xl text-headline-xl text-on-surface max-w-2xl font-bold">
              Deterministic compilation meets contextual intelligence.
            </h2>
            <p className="font-body-lg text-body-lg text-on-surface-variant max-w-xl mt-3">
              EVUA replaces speculative rewrite projects with a predictable, zero-hallucination compiler engine.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Step 1 */}
            <div className="flex flex-col p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 group border border-surface-container-highest/60">
              <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-on-primary transition-colors mb-6 shadow-sm">
                <span className="material-symbols-outlined text-[26px]">radar</span>
              </div>
              <div className="font-mono text-xs text-outline mb-1 uppercase tracking-wider font-semibold">Step 01</div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">Codebase Graph Analysis</h3>
              <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
                Traverses legacy repository syntax trees to construct a complete graph of dependencies, hidden globals, raw database calls, and scope leaks.
              </p>
              <div className="mt-auto pt-4 bg-surface-container-low rounded-xl p-3 font-mono text-xs text-on-surface-variant border border-surface-container-high">
                <span className="text-tertiary font-bold">✓</span> 1,482 controllers parsed<br />
                <span className="text-tertiary font-bold">✓</span> 29 circular hooks mapped
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 group border border-surface-container-highest/60">
              <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-on-primary transition-colors mb-6 shadow-sm">
                <span className="material-symbols-outlined text-[26px]">account_tree</span>
              </div>
              <div className="font-mono text-xs text-outline mb-1 uppercase tracking-wider font-semibold">Step 02</div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">Deterministic AST Rewriter</h3>
              <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
                Over 85% of legacy syntactic structures are transposed using formal syntax tree manipulation rules, ensuring guaranteed compilation without AI drift.
              </p>
              <div className="mt-auto pt-4 bg-surface-container-low rounded-xl p-3 font-mono text-xs text-on-surface-variant border border-surface-container-high">
                <span className="text-primary font-semibold">AST Pattern Engine:</span><br />
                <span className="text-secondary-container bg-inverse-surface px-1.5 py-0.5 rounded text-[11px]">$scope.x → signal(x)</span>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 group border border-surface-container-highest/60">
              <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center text-secondary group-hover:bg-secondary group-hover:text-on-secondary transition-colors mb-6 shadow-sm">
                <span className="material-symbols-outlined text-[26px]">psychology_alt</span>
              </div>
              <div className="font-mono text-xs text-outline mb-1 uppercase tracking-wider font-semibold">Step 03</div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">Semantic AI Synthesis</h3>
              <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
                Our scoped code LLM interprets messy idiomatic logic, converting legacy callbacks to reactive streams, async/await, and modern design patterns.
              </p>
              <div className="mt-auto pt-4 bg-surface-container-low rounded-xl p-3 font-mono text-xs text-on-surface-variant border border-surface-container-high">
                <span className="text-tertiary font-bold">✓</span> Callback spaghetti → async/await<br />
                <span className="text-tertiary font-bold">✓</span> 100% Type-safe interfaces
              </div>
            </div>

            {/* Step 4 */}
            <div className="flex flex-col p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 group border border-surface-container-highest/60">
              <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center text-tertiary group-hover:bg-tertiary group-hover:text-on-tertiary transition-colors mb-6 shadow-sm">
                <span className="material-symbols-outlined text-[26px]">checklist_rtl</span>
              </div>
              <div className="font-mono text-xs text-outline mb-1 uppercase tracking-wider font-semibold">Step 04</div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">Automated Test &amp; PR Diffs</h3>
              <p className="text-sm text-on-surface-variant mb-6 leading-relaxed">
                Generates side-by-side Git Pull Requests, auto-synthesizes unit tests for behavioral parity, and runs headless integration checks before merge.
              </p>
              <div className="mt-auto pt-4 bg-surface-container-low rounded-xl p-3 font-mono text-xs text-on-surface-variant border border-surface-container-high">
                <span className="text-tertiary font-bold">100% Test Pass Rate</span><br />
                <span className="text-outline">PR branch: evua/modern-v18</span>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* 4. INTERACTIVE SIDE-BY-SIDE DIFF LAB       */}
        {/* ========================================== */}
        <section id="diff-lab" className="w-full bg-surface-container-low py-20 border-y border-surface-container-highest/60">
          <div className="max-w-[1440px] mx-auto px-6 md:px-12">
            <div className="flex flex-col lg:flex-row items-start lg:items-end justify-between gap-6 mb-8">
              <div>
                <span className="font-mono text-xs uppercase tracking-wider text-primary font-bold">Live Migration Engine</span>
                <h2 className="font-headline-xl text-headline-xl text-on-surface mt-1 font-bold">Interactive Transformation Diff</h2>
                <p className="text-sm text-on-surface-variant mt-2 max-w-xl">
                  Inspect real AST nodes undergoing refactoring. Switch frameworks to observe deterministic syntax mapping.
                </p>
              </div>
              {/* Metric Badges */}
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-lowest shadow-sm border border-surface-container-high">
                  <span className="w-2.5 h-2.5 rounded-full bg-tertiary" />
                  <span className="font-mono text-xs text-on-surface font-semibold">96.4% Deterministic</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-lowest shadow-sm border border-surface-container-high">
                  <span className="material-symbols-outlined text-primary text-[16px]">security</span>
                  <span className="font-mono text-xs text-on-surface font-semibold">Zero Injection Leaks</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container-lowest shadow-sm border border-surface-container-high">
                  <span className="material-symbols-outlined text-secondary text-[16px]">speed</span>
                  <span className="font-mono text-xs text-on-surface font-semibold">12x Faster Dev Cycle</span>
                </div>
              </div>
            </div>

            {/* Tab Buttons */}
            <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-2">
              <button
                onClick={() => setActiveDiffTab('angular')}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-all flex items-center gap-2 ${
                  activeDiffTab === 'angular'
                    ? 'bg-primary text-on-primary shadow-md'
                    : 'bg-surface-container hover:bg-surface-container-high text-on-surface'
                }`}
              >
                <span>AngularJS 1.x → Angular 18 (Signals)</span>
              </button>
              <button
                onClick={() => setActiveDiffTab('php')}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-all flex items-center gap-2 ${
                  activeDiffTab === 'php'
                    ? 'bg-primary text-on-primary shadow-md'
                    : 'bg-surface-container hover:bg-surface-container-high text-on-surface'
                }`}
              >
                <span>PHP 5.6 (mysql_*) → PHP 8.3 (PDO Typed)</span>
              </button>
              <button
                onClick={() => setActiveDiffTab('vue')}
                className={`px-4 py-2 rounded-lg font-semibold text-sm transition-all flex items-center gap-2 ${
                  activeDiffTab === 'vue'
                    ? 'bg-primary text-on-primary shadow-md'
                    : 'bg-surface-container hover:bg-surface-container-high text-on-surface'
                }`}
              >
                <span>Vue 2 Options → Vue 3 &lt;script setup&gt;</span>
              </button>
            </div>

            {/* Split IDE Viewport */}
            <div className="code-diff-window rounded-2xl overflow-hidden shadow-2xl bg-inverse-surface border border-slate-700">
              {/* IDE Window Chrome */}
              <div className="px-4 py-3 bg-[#1e2129] flex items-center justify-between border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                  <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                  <span className="font-mono text-xs text-slate-400 ml-3">{currentDiff.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded bg-surface-container-highest/10 text-slate-300 font-mono text-[10px]">Unified Diff Mode</span>
                  <span className="px-2 py-0.5 rounded bg-primary/20 text-primary-fixed font-mono text-[10px]">Strict Mode Enabled</span>
                </div>
              </div>

              {/* Code Panels Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-800">
                {/* Legacy Side (Left) */}
                <div className="p-6 bg-[#16181f] text-slate-300 font-mono text-xs leading-relaxed overflow-x-auto min-h-[300px]">
                  <div className="flex items-center justify-between pb-3 mb-3 text-slate-400 font-semibold text-[11px] uppercase tracking-wider border-b border-slate-800/80">
                    <span className="flex items-center gap-1.5 text-rose-400">
                      <span className="material-symbols-outlined text-[14px]">remove_circle</span>
                      {currentDiff.legacyName}
                    </span>
                    <span className="text-slate-500">Deprecated</span>
                  </div>
                  <pre className="font-mono leading-6"><code>{currentDiff.legacyCode}</code></pre>
                </div>

                {/* Target Modern Side (Right) */}
                <div className="p-6 bg-[#0f1117] text-slate-200 font-mono text-xs leading-relaxed overflow-x-auto min-h-[300px]">
                  <div className="flex items-center justify-between pb-3 mb-3 text-slate-400 font-semibold text-[11px] uppercase tracking-wider border-b border-slate-800/80">
                    <span className="flex items-center gap-1.5 text-emerald-400">
                      <span className="material-symbols-outlined text-[14px]">add_circle</span>
                      {currentDiff.modernName}
                    </span>
                    <span className="text-emerald-400 font-semibold">{currentDiff.badge}</span>
                  </div>
                  <pre className="font-mono leading-6"><code>{currentDiff.modernCode}</code></pre>
                </div>
              </div>

              {/* Annotation Callout Strip */}
              <div className="p-4 bg-[#12141a] flex flex-wrap items-center justify-between gap-4 text-xs font-mono text-slate-300 border-t border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-secondary-container text-[18px]">auto_awesome</span>
                  <span>{currentDiff.ruleText}</span>
                </div>
                <Link to="/project/new" className="inline-flex items-center gap-1 text-primary-fixed hover:text-white transition-colors font-semibold">
                  <span>Try in Sandbox</span>
                  <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* 5. SUPPORTED MIGRATION PATHS (Grid)        */}
        {/* ========================================== */}
        <section id="stacks" className="w-full max-w-[1440px] mx-auto px-6 md:px-12 py-24">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-16">
            <div>
              <span className="font-mono text-xs uppercase tracking-wider text-primary font-bold">Comprehensive Stack Coverage</span>
              <h2 className="font-headline-xl text-headline-xl text-on-surface mt-1 font-bold">Battle-Tested Migration Paths</h2>
            </div>
            <p className="text-sm text-on-surface-variant max-w-md">
              Every pipeline comes with hardened, unit-tested transformation grammar rules tailored for enterprise architectures.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Card 1 */}
            <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between border border-surface-container-highest/60">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="w-10 h-10 rounded-xl bg-red-600/10 text-red-600 flex items-center justify-center font-bold text-sm">NG</span>
                  <span className="px-2.5 py-1 rounded-full bg-tertiary-fixed/40 text-tertiary font-mono text-xs font-bold">96% Automated</span>
                </div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">AngularJS → Angular 18+</h3>
                <p className="text-sm text-on-surface-variant mb-4">
                  Directly converts <code>$scope</code>, directive DDO configs, and filters into Standalone Components, typed Signals, and standard injectables.
                </p>
              </div>
              <div className="pt-4 flex items-center justify-between text-outline font-mono text-xs border-t border-surface-container-high/60">
                <span>Rules: 340+ AST specs</span>
                <Link to="/project/new" className="text-primary font-semibold flex items-center hover:underline">Start Path →</Link>
              </div>
            </div>

            {/* Card 2 */}
            <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between border border-surface-container-highest/60">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="w-10 h-10 rounded-xl bg-indigo-600/10 text-indigo-600 flex items-center justify-center font-bold text-sm">PHP</span>
                  <span className="px-2.5 py-1 rounded-full bg-tertiary-fixed/40 text-tertiary font-mono text-xs font-bold">94% Automated</span>
                </div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">PHP 5.6 → PHP 8.3 Modern</h3>
                <p className="text-sm text-on-surface-variant mb-4">
                  Removes deprecated <code>mysql_*</code>, transposes untyped arrays to typed DTOs/Enums, and modernizes CodeIgniter/Zend to Symfony or Laravel.
                </p>
              </div>
              <div className="pt-4 flex items-center justify-between text-outline font-mono text-xs border-t border-surface-container-high/60">
                <span>Rules: 480+ AST specs</span>
                <Link to="/project/new" className="text-primary font-semibold flex items-center hover:underline">Start Path →</Link>
              </div>
            </div>

            {/* Card 3 */}
            <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between border border-surface-container-highest/60">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="w-10 h-10 rounded-xl bg-emerald-600/10 text-emerald-600 flex items-center justify-center font-bold text-sm">VUE</span>
                  <span className="px-2.5 py-1 rounded-full bg-tertiary-fixed/40 text-tertiary font-mono text-xs font-bold">98% Automated</span>
                </div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">Vue 2 Options → Vue 3 Script Setup</h3>
                <p className="text-sm text-on-surface-variant mb-4">
                  Translates Vuex state stores to Pinia, rewrites mixins into clean composables, and transforms options boilerplate into script setup TypeScript.
                </p>
              </div>
              <div className="pt-4 flex items-center justify-between text-outline font-mono text-xs border-t border-surface-container-high/60">
                <span>Rules: 220+ AST specs</span>
                <Link to="/project/new" className="text-primary font-semibold flex items-center hover:underline">Start Path →</Link>
              </div>
            </div>

            {/* Card 4 */}
            <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between border border-surface-container-highest/60">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="w-10 h-10 rounded-xl bg-cyan-600/10 text-cyan-600 flex items-center justify-center font-bold text-sm">REA</span>
                  <span className="px-2.5 py-1 rounded-full bg-tertiary-fixed/40 text-tertiary font-mono text-xs font-bold">91% Automated</span>
                </div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">AngularJS 1.x → React 18 / Next.js</h3>
                <p className="text-sm text-on-surface-variant mb-4">
                  Re-architects legacy controller hierarchies into React functional hooks, TanStack Query states, and modern modular UI components.
                </p>
              </div>
              <div className="pt-4 flex items-center justify-between text-outline font-mono text-xs border-t border-surface-container-high/60">
                <span>Rules: 310+ AST specs</span>
                <Link to="/project/new" className="text-primary font-semibold flex items-center hover:underline">Start Path →</Link>
              </div>
            </div>

            {/* Card 5 */}
            <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between border border-surface-container-highest/60">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="w-10 h-10 rounded-xl bg-amber-600/10 text-amber-600 flex items-center justify-center font-bold text-sm">PY</span>
                  <span className="px-2.5 py-1 rounded-full bg-tertiary-fixed/40 text-tertiary font-mono text-xs font-bold">95% Automated</span>
                </div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">Python 2.7 → Python 3.12</h3>
                <p className="text-sm text-on-surface-variant mb-4">
                  Cleanses legacy string vs unicode ambiguities, refactors async generators, introduces strict typing hints via Pydantic and native type guards.
                </p>
              </div>
              <div className="pt-4 flex items-center justify-between text-outline font-mono text-xs border-t border-surface-container-high/60">
                <span>Rules: 190+ AST specs</span>
                <Link to="/project/new" className="text-primary font-semibold flex items-center hover:underline">Start Path →</Link>
              </div>
            </div>

            {/* Card 6 */}
            <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col justify-between border border-surface-container-highest/60">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="w-10 h-10 rounded-xl bg-red-800/10 text-red-800 flex items-center justify-center font-bold text-sm">JV</span>
                  <span className="px-2.5 py-1 rounded-full bg-tertiary-fixed/40 text-tertiary font-mono text-xs font-bold">92% Automated</span>
                </div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface mb-2 font-bold">Java 8 → Java 21 LTS (Spring 3)</h3>
                <p className="text-sm text-on-surface-variant mb-4">
                  Replaces old boilerplate with Java Records, Virtual Threads, pattern matching switch expressions, and modern Jakarta EE packages.
                </p>
              </div>
              <div className="pt-4 flex items-center justify-between text-outline font-mono text-xs border-t border-surface-container-high/60">
                <span>Rules: 410+ AST specs</span>
                <Link to="/project/new" className="text-primary font-semibold flex items-center hover:underline">Start Path →</Link>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* 6. METRICS & ROI HIGHLIGHTS (Bento Strip)  */}
        {/* ========================================== */}
        <section className="w-full bg-inverse-surface text-inverse-on-surface py-20 relative overflow-hidden">
          <div className="absolute -top-32 -left-32 w-96 h-96 bg-primary/20 rounded-full blur-[100px] pointer-events-none" />
          <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-secondary-container/20 rounded-full blur-[100px] pointer-events-none" />
          <div className="max-w-[1440px] mx-auto px-6 md:px-12 relative z-10">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="flex flex-col p-6 rounded-2xl bg-white/5 backdrop-blur-md border border-white/10">
                <span className="font-display text-[3.5rem] font-bold tracking-tight text-secondary-container mb-1">12M+</span>
                <span className="font-headline-sm text-headline-sm text-white mb-2 font-bold">Lines of Code Migrated</span>
                <p className="text-sm text-slate-400">Successfully refactored across complex monolithic backends and SPAs.</p>
              </div>
              <div className="flex flex-col p-6 rounded-2xl bg-white/5 backdrop-blur-md border border-white/10">
                <span className="font-display text-[3.5rem] font-bold tracking-tight text-tertiary-fixed mb-1">85%</span>
                <span className="font-headline-sm text-headline-sm text-white mb-2 font-bold">Engineering Hours Saved</span>
                <p className="text-sm text-slate-400">Eliminates mundane syntax rewrite drudgery; developers focus on domain verification.</p>
              </div>
              <div className="flex flex-col p-6 rounded-2xl bg-white/5 backdrop-blur-md border border-white/10">
                <span className="font-display text-[3.5rem] font-bold tracking-tight text-primary-fixed mb-1">0</span>
                <span className="font-headline-sm text-headline-sm text-white mb-2 font-bold">Unplanned Downtime</span>
                <p className="text-sm text-slate-400">Deterministic rollback guarantees and parallel runtime flags prevent release regression.</p>
              </div>
              <div className="flex flex-col p-6 rounded-2xl bg-white/5 backdrop-blur-md border border-white/10">
                <span className="font-display text-[3.5rem] font-bold tracking-tight text-white mb-1">3.8x</span>
                <span className="font-headline-sm text-headline-sm text-white mb-2 font-bold">Feature Velocity Post-Run</span>
                <p className="text-sm text-slate-400">Modern developer tooling and typed CI/CD accelerates subsequent team releases.</p>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* 7. ENTERPRISE COMPLIANCE & SECURITY        */}
        {/* ========================================== */}
        <section id="security" className="w-full max-w-[1440px] mx-auto px-6 md:px-12 py-24">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-5 flex flex-col gap-4">
              <span className="font-mono text-xs uppercase tracking-wider text-primary font-bold">Zero-Trust Environment</span>
              <h2 className="font-headline-xl text-headline-xl text-on-surface font-bold">Your intellectual property never leaves your custody.</h2>
              <p className="text-base text-on-surface-variant leading-relaxed">
                Designed specifically for regulated enterprises. EVUA operates either air-gapped on-premise, inside your isolated VPC, or through zero-retention ephemeral compilation runners.
              </p>
              <div className="flex flex-col gap-3 pt-4">
                <div className="flex items-center gap-3">
                  <span className="w-6 h-6 rounded-full bg-tertiary-fixed/50 text-tertiary flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[16px]">check</span>
                  </span>
                  <span className="text-sm font-medium text-on-surface">Zero Data Retention: Model training on client code is physically disabled</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-6 h-6 rounded-full bg-tertiary-fixed/50 text-tertiary flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[16px]">check</span>
                  </span>
                  <span className="text-sm font-medium text-on-surface">SOC 2 Type II Certified &amp; ISO 27001 audited pipelines</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-6 h-6 rounded-full bg-tertiary-fixed/50 text-tertiary flex items-center justify-center shrink-0">
                    <span className="material-symbols-outlined text-[16px]">check</span>
                  </span>
                  <span className="text-sm font-medium text-on-surface">Native GitHub Enterprise Server, GitLab Self-Managed, &amp; Bitbucket integrations</span>
                </div>
              </div>
            </div>

            {/* Right Visual Grid of Security Badges */}
            <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm flex flex-col gap-3 border border-surface-container-highest/60">
                <span className="material-symbols-outlined text-primary text-[32px]">lan</span>
                <h4 className="font-headline-sm text-headline-sm text-on-surface font-bold">On-Premises / VPC Ready</h4>
                <p className="text-sm text-on-surface-variant">
                  Deploy EVUA container daemon into AWS ECS, Google Cloud GKE, or self-hosted Kubernetes clusters.
                </p>
              </div>
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm flex flex-col gap-3 border border-surface-container-highest/60">
                <span className="material-symbols-outlined text-secondary text-[32px]">lock</span>
                <h4 className="font-headline-sm text-headline-sm text-on-surface font-bold">End-to-End Encryption</h4>
                <p className="text-sm text-on-surface-variant">
                  All transient AST tokens encrypted with customer-managed AWS KMS / Vault keys in flight and at rest.
                </p>
              </div>
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm flex flex-col gap-3 border border-surface-container-highest/60">
                <span className="material-symbols-outlined text-tertiary text-[32px]">verified_user</span>
                <h4 className="font-headline-sm text-headline-sm text-on-surface font-bold">Deterministic AST Verification</h4>
                <p className="text-sm text-on-surface-variant">
                  Formal mathematical proof verifying that the modern syntax tree is semantically identical to legacy source code.
                </p>
              </div>
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm flex flex-col gap-3 border border-surface-container-highest/60">
                <span className="material-symbols-outlined text-primary-container text-[32px]">policy</span>
                <h4 className="font-headline-sm text-headline-sm text-on-surface font-bold">Role-Based Access Control</h4>
                <p className="text-sm text-on-surface-variant">
                  Integrate with Okta, Azure AD, SAML 2.0, and enforce mandatory peer code reviews prior to PR emission.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* 8. DEVELOPER TESTIMONIALS & CASE STUDIES   */}
        {/* ========================================== */}
        <section className="w-full bg-surface-container-low py-20 border-t border-surface-container-highest/60">
          <div className="max-w-[1440px] mx-auto px-6 md:px-12">
            <div className="flex flex-col items-center text-center mb-16">
              <span className="font-mono text-xs uppercase tracking-wider text-primary font-bold">Engineering Validation</span>
              <h2 className="font-headline-xl text-headline-xl text-on-surface mt-1 font-bold">Real Teams. Months Saved.</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Review 1 */}
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm flex flex-col justify-between border border-surface-container-highest/60">
                <div>
                  <div className="flex items-center gap-1 text-amber-500 mb-4">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <span key={i} className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                    ))}
                  </div>
                  <p className="text-sm text-on-surface leading-relaxed mb-6 italic">
                    “We had a 700k LOC AngularJS monolith running our trading dashboard. A manual rewrite was estimated at 18 months with 8 full-time devs. EVUA completed the conversion to Angular 18 in three weeks.”
                  </p>
                </div>
                <div className="flex items-center gap-3 pt-4 border-t border-surface-container-high/60">
                  <div className="w-10 h-10 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold font-headline-sm">
                    MS
                  </div>
                  <div>
                    <div className="font-semibold text-sm text-on-surface">Marcus Sterling</div>
                    <div className="text-xs text-on-surface-variant">VP of Engineering, Apex FinTech</div>
                  </div>
                </div>
              </div>

              {/* Review 2 */}
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm flex flex-col justify-between border border-surface-container-highest/60">
                <div>
                  <div className="flex items-center gap-1 text-amber-500 mb-4">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <span key={i} className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                    ))}
                  </div>
                  <p className="text-sm text-on-surface leading-relaxed mb-6 italic">
                    “Upgrading 15-year-old PHP 5.6 raw SQL modules to modern strict PHP 8.3 was terrifying for our compliance team. EVUA’s deterministic AST safety rules gave us total confidence.”
                  </p>
                </div>
                <div className="flex items-center gap-3 pt-4 border-t border-surface-container-high/60">
                  <div className="w-10 h-10 rounded-full bg-secondary-container/20 text-secondary flex items-center justify-center font-bold font-headline-sm">
                    EC
                  </div>
                  <div>
                    <div className="font-semibold text-sm text-on-surface">Elena Chen</div>
                    <div className="text-xs text-on-surface-variant">Chief Software Architect, Synapse Med</div>
                  </div>
                </div>
              </div>

              {/* Review 3 */}
              <div className="p-6 rounded-2xl bg-surface-container-lowest shadow-sm flex flex-col justify-between border border-surface-container-highest/60">
                <div>
                  <div className="flex items-center gap-1 text-amber-500 mb-4">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <span key={i} className="material-symbols-outlined text-[18px]" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                    ))}
                  </div>
                  <p className="text-sm text-on-surface leading-relaxed mb-6 italic">
                    “The side-by-side diff review UI made PR sign-offs exceptionally fast. Our developers actually enjoyed reviewing the refactored code because it followed pristine modern idioms.”
                  </p>
                </div>
                <div className="flex items-center gap-3 pt-4 border-t border-surface-container-high/60">
                  <div className="w-10 h-10 rounded-full bg-tertiary-container/20 text-tertiary flex items-center justify-center font-bold font-headline-sm">
                    DK
                  </div>
                  <div>
                    <div className="font-semibold text-sm text-on-surface">David Kowalski</div>
                    <div className="text-xs text-on-surface-variant">Staff Platform Lead, Strata Cloud</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================== */}
        {/* 9. BOTTOM CONVERSION CTA BANNER            */}
        {/* ========================================== */}
        <section className="w-full max-w-[1440px] mx-auto px-6 md:px-12 py-20">
          <div className="relative rounded-3xl bg-inverse-surface text-inverse-on-surface p-8 lg:p-14 overflow-hidden shadow-2xl border border-slate-700">
            {/* Ambient Lighting Inside Banner */}
            <div className="absolute -top-24 right-1/4 w-[450px] h-[300px] bg-gradient-to-r from-primary to-secondary-container opacity-25 blur-[90px] pointer-events-none" />
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative z-10">
              <div className="lg:col-span-7 flex flex-col gap-4">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-primary-fixed font-mono text-xs uppercase tracking-wider self-start font-semibold">
                  Instant AST Assessment
                </div>
                <h2 className="font-headline-xl text-headline-xl text-white font-bold">
                  Ready to retire your legacy tech debt?
                </h2>
                <p className="text-base text-slate-300 max-w-xl">
                  Run EVUA CLI dry-run scanner on your repository in under 2 minutes. Get a full complexity scorecard, dependency health graph, and modernization roadmap.
                </p>
                <div className="flex flex-wrap items-center gap-4 pt-2">
                  <Link
                    to="/project/new"
                    className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full bg-primary hover:bg-primary-container text-on-primary transition-all font-semibold shadow-lg group"
                  >
                    <span>Start Free Migration Trial</span>
                    <span className="material-symbols-outlined text-[18px] group-hover:translate-x-1 transition-transform">arrow_forward</span>
                  </Link>
                  <a
                    href="https://github.com"
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-5 py-3.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors font-semibold"
                  >
                    <span className="material-symbols-outlined text-[18px]">terminal</span>
                    <span>View Docs &amp; CLI</span>
                  </a>
                </div>
              </div>

              {/* Terminal Widget */}
              <div className="lg:col-span-5">
                <div className="rounded-xl bg-[#0b0e14] p-4 shadow-2xl font-mono text-xs border border-slate-800">
                  <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
                    <div className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                      <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                      <span className="text-slate-400 text-[11px] ml-2 font-mono">bash — evua-cli</span>
                    </div>
                    <button
                      onClick={copyCliCommand}
                      className="text-slate-400 hover:text-white transition-colors flex items-center gap-1 text-[11px] px-2 py-1 rounded hover:bg-slate-800"
                    >
                      <span className="material-symbols-outlined text-[14px]">{copied ? 'check' : 'content_copy'}</span>
                      <span>{copied ? 'Copied!' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="space-y-1.5 leading-relaxed">
                    <div className="text-slate-300">
                      <span className="text-emerald-400">$</span> npx @evua/cli scan ./legacy-app
                    </div>
                    <div className="text-slate-500">&gt; Parsing 420 source files with Babel &amp; PhpParser...</div>
                    <div className="text-slate-500">&gt; Building AST dependency graph...</div>
                    <div className="text-emerald-400">✓ 94.2% Automatic Rewrite Confidence</div>
                    <div className="text-sky-300">✓ Estimated time saved: 640 engineering hours</div>
                    <div className="text-primary-fixed pt-1">→ Report ready: https://evua.dev/report/x79a2c</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="w-full bg-surface-container-lowest border-t border-surface-container-highest relative z-10">
        <div className="max-w-[1440px] mx-auto px-6 md:px-12 pt-12 pb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-8">
            <div className="lg:col-span-4 flex flex-col gap-4">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <span className="w-1.5 h-5 rounded-full bg-primary -skew-x-12" />
                  <span className="w-1.5 h-6 rounded-full bg-primary-container -skew-x-12" />
                  <span className="w-1.5 h-4 rounded-full bg-secondary-container -skew-x-12" />
                </div>
                <span className="font-headline-sm text-headline-sm font-bold tracking-tight text-on-surface">EVUA</span>
              </div>
              <p className="text-sm text-on-surface-variant max-w-sm">
                Automated, AI-assisted migration of legacy applications to modern, maintainable codebases.
              </p>
              <div className="flex items-center gap-2 pt-2">
                <a className="w-9 h-9 rounded-lg border border-outline-variant flex items-center justify-center text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors" href="https://github.com" target="_blank" rel="noreferrer">
                  <span className="material-symbols-outlined text-[20px]">code</span>
                </a>
                <a className="w-9 h-9 rounded-lg border border-outline-variant flex items-center justify-center text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors" href="#">
                  <span className="material-symbols-outlined text-[20px]">chat</span>
                </a>
                <a className="w-9 h-9 rounded-lg border border-outline-variant flex items-center justify-center text-on-surface-variant hover:text-primary hover:bg-surface-container transition-colors" href="#">
                  <span className="material-symbols-outlined text-[20px]">share</span>
                </a>
              </div>
            </div>

            <div className="lg:col-span-2 flex flex-col gap-3">
              <h4 className="font-mono text-xs uppercase tracking-wider text-on-surface font-bold">Product</h4>
              <ul className="flex flex-col gap-2 text-sm text-on-surface-variant">
                <li><a className="hover:text-primary transition-colors" href="#how-it-works">AST Transformation</a></li>
                <li><a className="hover:text-primary transition-colors" href="#how-it-works">AI Verification</a></li>
                <li><a className="hover:text-primary transition-colors" href="#diff-lab">Side-by-side Diff</a></li>
                <li><a className="hover:text-primary transition-colors" href="#stacks">Supported Stacks</a></li>
              </ul>
            </div>

            <div className="lg:col-span-2 flex flex-col gap-3">
              <h4 className="font-mono text-xs uppercase tracking-wider text-on-surface font-bold">Migrations</h4>
              <ul className="flex flex-col gap-2 text-sm text-on-surface-variant">
                <li><a className="hover:text-primary transition-colors" href="#stacks">AngularJS to Angular 18+</a></li>
                <li><a className="hover:text-primary transition-colors" href="#stacks">PHP 5.6 to PHP 8.x+</a></li>
                <li><a className="hover:text-primary transition-colors" href="#stacks">Vue 2 to Vue 3</a></li>
                <li><a className="hover:text-primary transition-colors" href="#stacks">Java 8 to Java 21</a></li>
              </ul>
            </div>

            <div className="lg:col-span-2 flex flex-col gap-3">
              <h4 className="font-mono text-xs uppercase tracking-wider text-on-surface font-bold">Resources</h4>
              <ul className="flex flex-col gap-2 text-sm text-on-surface-variant">
                <li><a className="hover:text-primary transition-colors" href="https://github.com" target="_blank" rel="noreferrer">Documentation</a></li>
                <li><a className="hover:text-primary transition-colors" href="#diff-lab">Interactive Sandbox</a></li>
                <li><a className="hover:text-primary transition-colors" href="https://github.com" target="_blank" rel="noreferrer">CLI Guide</a></li>
                <li><a className="hover:text-primary transition-colors" href="#security">Security &amp; SOC2</a></li>
              </ul>
            </div>

            <div className="lg:col-span-2 flex flex-col gap-3">
              <h4 className="font-mono text-xs uppercase tracking-wider text-on-surface font-bold">Company</h4>
              <ul className="flex flex-col gap-2 text-sm text-on-surface-variant">
                <li><a className="hover:text-primary transition-colors" href="#security">Privacy &amp; Security</a></li>
                <li><a className="hover:text-primary transition-colors" href="#">Terms of Service</a></li>
                <li><Link className="hover:text-primary transition-colors" to="/project/new">Start Project</Link></li>
                <li><Link className="hover:text-primary transition-colors" to="/history">History Portal</Link></li>
              </ul>
            </div>
          </div>

          <div className="mt-12 pt-6 border-t border-surface-container-highest flex flex-col sm:flex-row items-center justify-between gap-4 text-on-surface-variant text-xs">
            <span>© 2025 EVUA, Inc. Deterministic refactoring engine. All rights reserved.</span>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-surface-container-low border border-surface-container-high">
              <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse" />
              <span className="font-mono text-on-surface font-semibold">All Transformation Pipelines Operational</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
