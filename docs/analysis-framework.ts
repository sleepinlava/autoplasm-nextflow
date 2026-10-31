/** AutoPlasm pipeline explainer. Compile with: tsc -p docs/tsconfig.json */
type PlatformKey = "illumina" | "ont" | "pacbio_hifi" | "hybrid" | "assembly";
type ConsensusMethod =
  "weighted_vote" | "majority_vote" | "intersection" | "single_tool";
type InputId = "binning" | "mag" | "linking" | "network" | "samples";
type SelectId = "stage-select" | "groups" | "profile" | "method";
type ButtonId =
  | "prev"
  | "next"
  | "play"
  | "copy-command"
  | "disagreement"
  | "export"
  | "print"
  | "motion";
type UIElement<Id extends string> = Id extends InputId
  ? HTMLInputElement
  : Id extends SelectId
    ? HTMLSelectElement
    : Id extends ButtonId
      ? HTMLButtonElement
      : Id extends "samples-value"
        ? HTMLOutputElement
        : HTMLElement;
interface Platform {
  label: string;
  input: string;
  qc: string;
  assembly: string;
  map: string;
  note: string;
}
interface Stage {
  id: string;
  name: string;
  tool: string;
  title: string;
  text: string;
  input: string;
  method: string;
  output: string;
  param: string;
  path: string;
  source: string;
  note: string;
}
interface Detector {
  id: string;
  name: string;
  w: number;
  on: boolean;
  yes: boolean;
}
function $<Id extends string>(id: Id): UIElement<Id> {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing UI element: ${id}`);
  return element as UIElement<Id>;
}

const state: { platform: PlatformKey; step: number } = {
  platform: "illumina",
  step: 4,
};
const platforms: Record<PlatformKey, Platform> = {
  illumina: {
    label: "Illumina",
    input: "read1 + read2",
    qc: "fastp · 可选 FastQC",
    assembly: "MEGAHIT / metaSPAdes",
    map: "bowtie2",
    note: "默认 Illumina 路线：fastp → MEGAHIT → QUAST / 覆盖度 → geNomad。提供 host_reference 时使用 bowtie2 去除宿主；MultiQC 默认开启。",
  },
  ont: {
    label: "ONT",
    input: "POD5 / BAM / FASTQ",
    qc: "NanoPlot + Filtlong",
    assembly: "metaFlye",
    map: "minimap2 · map-ont",
    note: "POD5 经过 Dorado，BAM 转为 FASTQ，再进入长读 QC 与组装；medaka 可选。Dorado 需单独安装。",
  },
  pacbio_hifi: {
    label: "PacBio HiFi",
    input: "BAM / HiFi FASTQ",
    qc: "HiFiAdapterFilt",
    assembly: "hifiasm-meta",
    map: "minimap2 · map-hifi",
    note: "BAM 可转换为 FASTQ；HiFiAdapterFilt 后由 hifiasm-meta 组装，比对使用 map-hifi。当前 HiFi 路线未接入 MultiQC。",
  },
  hybrid: {
    label: "Hybrid",
    input: "双端短读 + ONT 长读",
    qc: "短读 + 长读 QC",
    assembly: "OPERA-MS / hybridSPAdes",
    map: "bowtie2 + map-ont",
    note: "当前 Hybrid 以 ONT 长读路径处理；默认 OPERA-MS 需单独安装。质粒定量分 short / long，跨样本质粒表取 short；contig 覆盖度合并两路。",
  },
  assembly: {
    label: "Assembly",
    input: "assembly FASTA",
    qc: "无 read QC",
    assembly: "用户提供的组装",
    map: "无 read-based 定量",
    note: "FASTA 直接进入 QUAST 与质粒检测，继续分型、注释和比较；跳过 read QC、定量、MAG、linking 与跨样本丰度统计。宿主模型需显式选择 PlasmidHostFinder。",
  },
};
function stages(): Stage[] {
  const p = platforms[state.platform],
    asm = state.platform === "assembly";
  return [
    {
      id: "00",
      name: "输入与转换",
      tool: "samplesheet / Dorado",
      title: "统一输入，保留每个样本的身份。",
      text: "main.nf 解析样本表，验证 sample_id 与平台字段，将输入文件和 meta 组成平台需要的 tuple。输入转换按材料类型触发。",
      input: p.input,
      method: asm
        ? "直接接收 assembly 列的 FASTA。"
        : state.platform === "illumina"
          ? "从 read1 / read2 构建配对短读通道。"
          : state.platform === "pacbio_hifi"
            ? "BAM 按需通过 samtools 转 FASTQ，或直接使用 HiFi FASTQ。"
            : "POD5 → Dorado；BAM → samtools FASTQ；已有 FASTQ 直接进入长读分支。",
      output: "平台输入通道；有转换时发布输入处理产物。",
      param: "--samplesheet / --platform / --dorado_model",
      path: "00_input_validation/",
      source: "main.nf",
      note: "sample_id 全表唯一；平台所需字段缺失时提前失败。",
    },
    {
      id: "01",
      name: "Reads 质控",
      tool: p.qc,
      title: "按平台处理 reads 的质量与污染。",
      text: "质控由各平台子工作流组织；提供宿主参考时再执行宿主去除。短读用 bowtie2，长读用 minimap2。",
      input: asm ? "当前平台无 reads。" : "输入 reads 或转换后的 FASTQ。",
      method: asm
        ? "Assembly 跳过此分支。"
        : p.qc + "；宿主去除由 host_reference 触发。",
      output: asm
        ? "无 read QC 产物。"
        : "清洁 reads、相应质控结果；按平台与开关汇总 MultiQC。",
      param: "--run_fastqc / --run_multiqc / --host_reference",
      path: "01_qc/",
      source: "subworkflows/" + state.platform + ".nf",
      note: "FastQC 默认关闭；HiFi 当前未接 MultiQC，不能仅凭全局开关视为已执行。",
    },
    {
      id: "02",
      name: "组装与覆盖度",
      tool: p.assembly,
      title: asm
        ? "使用已有 contigs，进入检测与评估。"
        : "从 reads 构建 contigs，再估计覆盖度。",
      text: asm
        ? "直接传递用户提供的组装 FASTA，不运行组装器，也不生成 read-based 覆盖度。"
        : "组装 FASTA 进入检测与组装评估；清洁 reads 回贴全组装，经 CONTIG_COVERAGE 形成 contig BAM 与覆盖度表。",
      input: asm
        ? "样本表中的 assembly FASTA。"
        : "质控 / 去宿主后的短读或长读。",
      method: asm
        ? "直接使用用户组装，不运行组装器和覆盖度链。"
        : p.assembly + "；覆盖度比对使用 " + p.map + "。",
      output: asm
        ? "传递输入 FASTA；无新组装、组装图或覆盖度产物。"
        : "组装 FASTA；可用时产出组装图、contig BAM 与 CoverM 表。",
      param: "--short_read_assembler / --hybrid_assembler",
      path: "02_assembly/ · coverage/",
      source: "subworkflows/" + state.platform + ".nf",
      note: "MEGAHIT 路线没有 metaSPAdes 的 FASTG 通道；图依赖工具还需要匹配输入。",
    },
    {
      id: "03",
      name: "组装评估",
      tool: "QUAST / 可选 medaka",
      title: "组装后，评估序列的基本特征。",
      text: "QUAST 读取组装 FASTA 并输出统计。ONT 可另行选择 medaka 抛光；它不等于所有平台必经的固定步骤。",
      input: "组装 FASTA；抛光另需适配的 ONT reads。",
      method: "QUAST；ONT medaka 由 polishing_tools 显式选择。",
      output: "组装统计及可选抛光产物。",
      param: "--polishing_tools medaka（ONT，可选）",
      path: "03_assembly_qc/ · polishing/",
      source: "subworkflows/" + state.platform + ".nf",
      note: "连续性统计用于评估组装，不能单独证明结构正确或质粒闭环。",
    },
    {
      id: "04",
      name: "质粒检测与共识",
      tool: "geNomad → consensus",
      title: "以 geNomad 为主干，形成候选质粒。",
      text: "PLASMID_DETECTION 统一调用必选 geNomad 与可选检测器。输出逐工具判定、共识 FASTA 和结构候选，供共享下游分支使用。",
      input: "组装 contigs。",
      method:
        "geNomad + 可选 PLASMe / PlasX / Platon → 共识 → 结构检测。",
      output: "predictions / consensus TSV、候选质粒 FASTA、结构 TSV。",
      param:
        "plasmid_detection_tools = ['genomad']；consensus_method = weighted_vote",
      path: "04_plasmid_detection/",
      source: "subworkflows/plasmid_detection.nf",
      note: "共识支持四种规则；结构脚本的 circular 为待复核标记，ITR 本身不足以证明闭环。",
    },
    {
      id: "05",
      name: "质粒分箱",
      tool: "MOB-recon / 可选分箱器",
      title: "需要时，把片段进一步组织为候选单元。",
      text: "分箱是 PLASMID_DOWNSTREAM 中的可选分支，与分型和注释并列。不同工具分别依赖覆盖度、组装图或 reads。",
      input: "候选 FASTA；按工具额外使用图、BAM、覆盖度或短读。",
      method:
        "PlasMAAG / gplas2 / MOB-recon / Recycler，默认列表为空。",
      output: "各分箱工具的独立产物。",
      param: "plasmid_binning_tools = []",
      path: "05_plasmid_binning/",
      source: "subworkflows/plasmid_downstream.nf",
      note: "分箱产物没有统一替换所有下游的共识 FASTA；不能把目录编号理解为串行重建。",
    },
    {
      id: "06",
      name: "质粒分型",
      tool: "PlasmidFinder + MOB-typer",
      title: "描述复制子与可移动性相关类型。",
      text: "共识候选 FASTA 同时进入默认分型工具。通过额外列表，可接入 COPLA 或转移系统相关模型。",
      input: "非空共识质粒 FASTA。",
      method:
        "默认 PlasmidFinder + MOB-typer；可选 COPLA / CONJScan / MacSyFinder。",
      output: "复制子、MOB 与相关分型结果。",
      param: "typing_tools = ['plasmidfinder','mob_typer']",
      path: "06_plasmid_typing/",
      source: "subworkflows/plasmid_downstream.nf",
      note: "MOB-typer 需要 mob_suite_db；可选 COPLA 需要对应参考图和列表。",
    },
    {
      id: "07",
      name: "宿主 profile 与关联",
      tool: asm ? "PlasmidHostFinder（可选）" : "MetaPhlAn / MAG / linking",
      title: "先描述群落，再按需推断宿主候选。",
      text: "HOST_PREDICTION 生成群落 profile；MAG_HOST 与 HOST_LINKING 提供可选扩展。三者具有独立开关与输入条件。",
      input: asm
        ? "候选质粒 FASTA，供显式启用的 PlasmidHostFinder。"
        : "清洁 reads、全组装及可用的覆盖度；关联可再使用 MAG / taxonomy / 长读 BAM。",
      method: asm
        ? "默认 MetaPhlAn 跳过；可显式启用 PlasmidHostFinder。"
        : "默认 MetaPhlAn；Kraken2 仅 Illumina 可选。MAG、共丰度 / 组成 / 长读桥接与 HOTSPOT 按需启用。",
      output: "群落 profile；实际启用并产出时的 MAG、分类、质量与候选关联表。",
      param: "mag_tools = []；host_plasmid_linking = false",
      path: "07_host_prediction/ · mag/ · linking/",
      source: "subworkflows/host_linking.nf",
      note: "CRISPR 未实现。MAG 最终通道路由与候选宿主的证据边界详见审查。",
    },
    {
      id: "08",
      name: "功能与元件注释",
      tool: "Bakta / AMRFinderPlus",
      title: "为质粒候选添加基因与功能上下文。",
      text: "共享下游把同一批候选传给默认注释工具，分别描述基因、耐药候选及可移动遗传元件。",
      input: "非空共识质粒 FASTA；工具对应的数据库。",
      method:
        "默认 Bakta、AMRFinderPlus、ISEScan、IntegronFinder；可选 Prodigal / ABRicate / RGI / eggNOG-mapper / MOB-suite。",
      output:
        "基因 / 蛋白及注释文件、AMR 候选、IS / integron；Bakta GBFF 可供 clinker。",
      param:
        "annotation_tools = ['bakta','amrfinderplus','isescan','integronfinder']",
      path: "08_annotation/",
      source: "subworkflows/plasmid_downstream.nf",
      note: "基因注释与表型 / 实际转移能力分别解释；启用数据库依赖工具需提供相应资源。",
    },
    {
      id: "09",
      name: "比较与目录",
      tool: "MMseqs2 / 可选比较",
      title: "收集跨样本候选，建立序列目录。",
      text: "COMPARATIVE 收集候选 FASTA，经 catalog 准备添加样本身份后交给 MMseqs2；序列比较和邻域展示可选。",
      input: "各样本候选 FASTA；clinker 需要 Bakta 结果。",
      method:
        "默认 MMseqs2：identity 0.95 / target coverage 0.8；可选 BLASTn / MUMmer / clinker。",
      output: "cluster TSV、代表序列 FASTA、可选比对与基因邻域结果。",
      param: "comparative_tools = ['mmseqs2']",
      path: "09_comparative_genomics/",
      source: "subworkflows/comparative.nf",
      note: "当前 catalog 未接回定量；聚类阈值不等于已验证的质粒物种界限。",
    },
    {
      id: "10",
      name: "质粒丰度",
      tool: asm ? "当前平台跳过" : p.map + " → CoverM",
      title: asm
        ? "已有组装，不运行 read-based 定量。"
        : "将 reads 回贴候选，计算质粒丰度。",
      text: asm
        ? "Assembly 路由未向 PLASMID_ABUNDANCE 提供 reads，因此不运行比对或 CoverM，也不产生丰度表。"
        : "PLASMID_ABUNDANCE 接收每样本候选及清洁 reads。短读用 bowtie2，长读用 minimap2，排序 BAM 交给 CoverM。",
      input: asm
        ? "当前平台无 reads，跳过。"
        : "本样本候选 FASTA 与清洁 reads。",
      method: asm
        ? "Assembly 不实例化此分支。"
        : p.map + " → CoverM mean / TPM / RPKM；Hybrid 保留短 / 长两套。",
      output: asm
        ? "当前平台无此阶段产物。"
        : "样本级质粒丰度表；Hybrid short / long，跨样本质粒表选 short。",
      param: "平台选择决定比对链；无独立默认关闭开关。",
      path: "10_abundance/",
      source: "subworkflows/plasmid_abundance.nf",
      note: "样本内丰度与共享参考测量分开；跨样本使用全组装精确去重参考重映射，raw_count 为 read 比对数，双端 mates 分开。",
    },
    {
      id: "11",
      name: "多样性与差异",
      tool: "vegan / 内部效应量",
      title: "收集合并表，再按条件执行统计。",
      text: "CROSS_SAMPLE 显式合并样本 ID 与丰度表；多样性、内部差异、可选 ANCOMBC2 / DESeq2 与网络读取共享 plasmid 表。",
      input: asm
        ? "无 read-based 丰度矩阵，跳过。"
        : "合并 contig / plasmid 长表及样本元数据。",
      method:
        "多样性 ≥3 样本；内部 Welch + Hedges’ g + BH，默认每组 ≥3；DESeq2 默认关闭。",
      output: asm
        ? "当前平台不生成丰度合并表或本阶段统计结果。"
        : "多样性指标、Bray–Curtis 距离、差异表；tables/ 的合并丰度长表。",
      param: "run_diversity = true；run_differential_internal = true",
      path: "11_diversity/ · tables/",
      source: "subworkflows/cross_sample.nf",
      note: "这些是运行门槛；统一特征目录、组成性、原始计数与设计适配仍需单独验收。",
    },
    {
      id: "12",
      name: "共变网络",
      tool: "FastSpar",
      title: "达到样本门槛后，可选估计共变结构。",
      text: "网络分支以 plasmid 丰度表准备矩阵，只有显式开启且样本总数达门槛时运行 FastSpar。",
      input: "合并 plasmid 表；默认样本数门槛 ≥20。",
      method: "NETWORK_PREPARE → FASTSPAR；默认关闭。",
      output: asm
        ? "当前平台无网络产物。"
        : "correlation.tsv 与 covariance.tsv。",
      param: "run_network = false；network_min_samples = 20",
      path: "12_network/",
      source: "modules/cross_sample/fastspar.nf",
      note: "通用质粒网络使用共享参考的整数 raw_count，尚未接 bootstrap / p 值；与 protocol 的 MAG–质粒关联分支不同，相关不等于互作。",
    },
    {
      id: "R",
      name: "报告与运行记录",
      tool: "Markdown / HTML / methods",
      title: "把各阶段产物汇总成可追溯的说明。",
      text: "REPORT 等待相关触发通道并生成分析汇总；Nextflow 另外输出执行时间线和流程运行报告。",
      input: "运行完成触发信息与发布到 outdir 的分析产物。",
      method:
        "generate_report.R；R Markdown 可用时渲染模板，否则使用简版 HTML。",
      output:
        "report.md / report.html / methods.md；pipeline_info/timeline.html 与 report.html。",
      param: "--outdir / --project_name；timeline / report 已配置。",
      path: "report/ · pipeline_info/",
      source: "modules/cross_sample/report.nf",
      note: "分析报告目前扫描 publish 目录，异步发布与旧结果混入风险详见事实审查。",
    },
  ];
}
const positions: [number, number][] = [
  [90, 85],
  [285, 85],
  [495, 85],
  [495, 210],
  [705, 85],
  [915, 210],
  [915, 85],
  [90, 335],
  [705, 210],
  [705, 335],
  [495, 335],
  [495, 460],
  [705, 460],
  [915, 460],
];
function skipped(i: number) {
  return state.platform === "assembly" && [1, 10, 11, 12].includes(i);
}
function optional(i: number) {
  return i === 5 || i === 12;
}
function enabled(i: number) {
  if (state.platform === "assembly" && [7, 12].includes(i)) return false;
  return i === 5
    ? $("binning").checked
    : i === 12
      ? $("network").checked
      : i === 7
        ? $("mag").checked || $("linking").checked
        : false;
}
function renderDiagram() {
  const s = stages();
  let svg = `<defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L8 4L0 8" fill="#638198"/></marker></defs><text class="overview-label" x="28" y="31">SAMPLE WORKFLOW</text>`;
  const edges: [string, number][] = [
    ["M170 85H205", 0],
    ["M365 85H415", 0],
    ["M575 85H625", 0],
    ["M785 85H835", 0],
    ["M495 115V180", 0],
    ["M705 115V180", 0],
    ["M785 100H810V210H835", 1],
    ["M440 115H390V335H365", 0],
    ["M285 115V280H90V305", 0],
    ["M665 115H600V335H575", 0],
    ["M785 115H815V335H785", 0],
    ["M705 240V305", 1],
    ["M365 335H390V460H415", 0],
    ["M495 365V430", 1],
    ["M575 350H600V405H705V430", 1],
    ["M785 335H915V430", 0],
    ["M575 475H600V510H835V475", 0],
    ["M785 460H835", 1],
    ["M415 335H390V390H90V365", 1],
  ];
  svg += edges
    .map(([d, opt]) => `<path d="${d}" class="dag-edge ${opt ? "opt" : ""}"/>`)
    .join("");
  svg += `<g opacity="${state.platform === "assembly" ? "0.28" : "1"}"><rect x="205" y="305" width="160" height="60" rx="6" fill="#0e1b25" stroke="#456071"/><text x="220" y="329" class="dag-caption">02 / CONTIG_COVERAGE</text><text x="220" y="348" class="dag-caption">组装回贴 · BAM / 覆盖度</text></g><text x="270" y="272" class="dag-caption">清洁 reads → profile</text><text x="395" y="447" class="dag-caption">共享质粒表</text><text x="611" y="399" class="dag-caption">plasmid 表</text><text x="718" y="289" class="dag-caption">可选 clinker</text><text x="28" y="533" class="dag-caption">依赖关系示意，省略部分 reads / 数据库 / 报告依赖；目录编号不是串行顺序。</text>`;
  svg += s
    .map((c, i) => {
      const [x, y] = positions[i];
      const shortTool =
        i === 2
          ? platforms[state.platform].assembly.split(" / ")[0]
          : i === 10
            ? state.platform === "assembly"
              ? "跳过"
              : state.platform === "illumina"
                ? "bowtie2 → CoverM"
                : "minimap2 / CoverM"
            : c.tool;
      return `<g class="dag-node ${state.step === i ? "selected" : ""} ${optional(i) ? "optional" : ""} ${enabled(i) ? "enabled" : ""} ${skipped(i) ? "skipped" : ""}" role="button" tabindex="0" data-step="${i}" aria-label="${c.id} ${c.name}" aria-pressed="${state.step === i}"><rect x="${x - 80}" y="${y - 30}" width="160" height="60" rx="6"/><text x="${x - 66}" y="${y - 7}" class="n-num">${c.id}</text><text x="${x - 42}" y="${y - 7}" class="n-name">${c.name}</text><text x="${x - 66}" y="${y + 15}" class="n-tool">${shortTool}</text></g>`;
    })
    .join("");
  $("dag").innerHTML = svg;
  $("mobile-stages").innerHTML = s
    .map(
      (c, i) =>
        `<button data-step="${i}" class="${skipped(i) ? "skipped" : ""}" aria-pressed="${i === state.step}">${c.id} · ${c.name}<span>${skipped(i) ? "所选平台跳过" : optional(i) ? (enabled(i) ? "演示已启用" : "默认关闭") : i === 7 && enabled(i) ? "演示扩展已启用" : "默认 / 按输入运行"}</span></button>`,
    )
    .join("");
}
function renderStage() {
  const c = stages()[state.step];
  $("chapter").innerHTML =
    `<div class="chapter-intro"><span class="eyebrow">STAGE ${c.id} / ${state.platform.toUpperCase()}</span><h3>${c.title}</h3><p>${c.text}</p><div class="formula">${c.tool}</div></div><div class="chapter-detail"><span class="tag ${skipped(state.step) ? "gold" : optional(state.step) ? "gold" : "blue"}">${skipped(state.step) ? "所选平台跳过" : optional(state.step) ? (enabled(state.step) ? "演示已开启的可选分支" : "可选分支 · 默认关闭") : "主干 / 按输入条件运行"}</span><dl>${[
      ["输入", c.input],
      ["工具", c.method],
      ["产物", c.output],
      ["参数", c.param],
      ["目录", c.path],
    ]
      .map(([k, v]) => `<div class="spec"><dt>${k}</dt><dd>${v}</dd></div>`)
      .join(
        "",
      )}</dl><p class="small">${c.note}</p><a class="small" href="../${c.source}">源码：${c.source} ↗</a></div>`;
  $("stage-select").value = String(state.step);
  $("step-count").textContent =
    String(state.step + 1).padStart(2, "0") + " / 14";
  $("prev").disabled = state.step === 0;
  $("next").disabled = state.step === 13;
  renderDiagram();
  $("print-stages").innerHTML = stages()
    .map(
      (c) =>
        `<article><h3>${c.id} · ${c.name}</h3><p>${c.text}<br>方法：${c.method}<br>产物：${c.output}<br>参数：${c.param}<br>目录：${c.path}</p></article>`,
    )
    .join("");
}
function selectStage(i: number) {
  state.step = Math.max(0, Math.min(13, i));
  renderStage();
}
let playTimer: ReturnType<typeof setInterval> | null = null;
function stopPlay() {
  if (playTimer !== null) clearInterval(playTimer);
  playTimer = null;
  $("play").textContent = "▶ 自动讲解";
  $("play").setAttribute("aria-pressed", "false");
}
function stageClick(e: Event) {
  if (!(e.target instanceof Element)) return;
  const el = e.target.closest<HTMLElement>("[data-step]");
  if (el) {
    stopPlay();
    selectStage(Number(el.dataset.step));
  }
}
$("dag").addEventListener("click", stageClick);
$("mobile-stages").addEventListener("click", stageClick);
$("dag").addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    stageClick(e);
  }
});
$("stage-select").innerHTML = stages()
  .map((c, i) => `<option value="${i}">${c.id} · ${c.name}</option>`)
  .join("");
$("stage-select").onchange = (e) => {
  stopPlay();
  selectStage(Number($("stage-select").value));
};
$("prev").onclick = () => {
  stopPlay();
  selectStage(state.step - 1);
};
$("next").onclick = () => {
  stopPlay();
  selectStage(state.step + 1);
};
$("play").onclick = () => {
  if (playTimer) {
    stopPlay();
    return;
  }
  if (state.step === 13) selectStage(0);
  $("play").textContent = "Ⅱ 暂停讲解";
  $("play").setAttribute("aria-pressed", "true");
  playTimer = setInterval(() => {
    selectStage(state.step + 1);
    if (state.step === 13) stopPlay();
  }, 12000);
};
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopPlay();
});
function renderPlatform() {
  const p = platforms[state.platform];
  const asm = state.platform === "assembly";
  $("platform-code").textContent = "--platform " + state.platform;
  $("platform-note").textContent = p.note;
  $("platform-strip").innerHTML = [
    ["输入材料", p.input, "samplesheet TSV"],
    ["质控路径", p.qc, asm ? "read QC skipped" : "QC / host removal"],
    [
      "组装器",
      p.assembly,
      asm ? "provided FASTA → contigs" : "assembly → contigs",
    ],
    ["定量比对", p.map, asm ? "abundance skipped" : "reads → BAM → CoverM"],
  ]
    .map(
      ([a, b, c]) =>
        `<div><small>${a}</small><b>${b}</b><code>${c}</code></div>`,
    )
    .join("");
  (["mag", "linking", "network"] as const).forEach((id) => {
    $(id).disabled = asm;
  });
  renderStage();
  renderConfig();
}
$("platforms").addEventListener("click", (e) => {
  if (!(e.target instanceof Element)) return;
  const el = e.target.closest<HTMLElement>("[data-platform]");
  if (!el || !el.dataset.platform || !(el.dataset.platform in platforms))
    return;
  stopPlay();
  state.platform = el.dataset.platform as PlatformKey;
  document
    .querySelectorAll("[data-platform]")
    .forEach((b) => b.setAttribute("aria-pressed", String(b === el)));
  renderPlatform();
});
function commandText() {
  const p = state.platform,
    asm = p === "assembly";
  let parts = [
    "nextflow run .",
    "  --platform " + p,
    "  --samplesheet /path/to/samples.tsv",
    "  --outdir results/run1",
    "  --genomad_db /db/genomad",
    "  --bakta_db /db/bakta",
    "  --amrfinderplus_db /db/amrfinder/latest",
    "  --mob_suite_db /db/mob_suite",
  ];
  if (!asm) parts.push("  --metaphlan_db /db/metaphlan");
  if ($("binning").checked) parts.push("  --plasmid_binning_tools mob_recon");
  if (!asm && $("mag").checked)
    parts.push(
      "  --mag_tools 'metabat2,checkm2,gtdbtk'",
      "  --checkm2_db /db/checkm2",
      "  --gtdbtk_db /db/gtdbtk",
    );
  if (!asm && $("linking").checked) parts.push("  --host_plasmid_linking true");
  if (!asm && $("network").checked) parts.push("  --run_network true");
  parts.push("  -profile " + $("profile").value);
  return parts.join(" \\\n");
}
function renderConfig() {
  const n = Number($("samples").value),
    g = Number($("groups").value),
    r = Math.floor(n / g),
    asm = state.platform === "assembly";
  $("samples-value").value = String(n);
  const rows = asm
    ? [
        ["多样性", "blocked", "Assembly 不生成丰度表。"],
        ["内部差异", "blocked", "当前平台跳过跨样本丰度统计。"],
        ["共变网络", "blocked", "当前平台不运行此分支。"],
      ]
    : [
        [
          "多样性",
          n >= 3 ? "conditional" : "blocked",
          n >= 3
            ? "默认开启，样本数达到 ≥3 门槛。"
            : "默认开启，但未达到 ≥3 样本门槛。",
        ],
        [
          "内部差异",
          g >= 2 && r >= 3 ? "conditional" : "blocked",
          g < 2
            ? "至少需要两组；当前一组。"
            : r < 3
              ? `最小组约 ${r} 个重复，低于默认 3。`
              : `最小组约 ${r} 个重复，达到默认门槛。`,
        ],
        [
          "共变网络",
          !$("network").checked
            ? "blocked"
            : n >= 20
              ? "conditional"
              : "blocked",
          !$("network").checked
            ? "默认关闭；可用上方开关开启。"
            : n < 20
              ? `已开启，但 n=${n}，低于 20 样本门槛。`
              : "已开启，样本数达到 ≥20 门槛。",
        ],
      ];
  $("runtime-gates").innerHTML = rows
    .map(
      ([a, b, c]) =>
        `<div class="gate" data-state="${b}"><b>${b === "blocked" ? "○" : "△"} ${a}</b><span>${c}</span></div>`,
    )
    .join("");
  $("command").textContent = commandText();
  const p = platforms[state.platform];
  $("runtime-path").textContent =
    p.input +
    " → " +
    (asm
      ? "QUAST → geNomad → 分型 / 注释 / 比较"
      : p.qc + " → " + p.assembly + " → geNomad → 并行下游 / 定量");
  $("platform-source").textContent =
    "main.nf → subworkflows/" + state.platform + ".nf → CROSS_SAMPLE";
}
(["binning", "mag", "linking", "network"] as const).forEach((id) =>
  $(id).addEventListener("change", () => {
    renderStage();
    renderConfig();
  }),
);
(["samples", "groups", "profile"] as const).forEach((id) =>
  $(id).addEventListener("input", renderConfig),
);
const detectors: Detector[] = [
  { id: "genomad", name: "geNomad", w: 0.6, on: true, yes: true },
  { id: "platon", name: "Platon", w: 0.15, on: false, yes: false },
  { id: "plasme", name: "PLASMe", w: 0.15, on: false, yes: false },
  { id: "plasx", name: "PlasX", w: 0.1, on: false, yes: false },
];
function detectorRows() {
  $("detectors").innerHTML = detectors
    .map(
      (d, i) =>
        `<div class="detector ${d.on ? "" : "off"}" id="row-${d.id}"><label><input type="checkbox" data-d="${i}" data-field="on" ${d.on ? "checked" : ""} ${i === 0 ? "disabled" : ""} aria-label="启用 ${d.name}">${d.name}${i === 0 ? " *" : ""}</label><input type="number" min="0" max="10" step="0.05" value="${d.w}" data-d="${i}" data-field="w" aria-label="${d.name} 权重" ${!d.on ? "disabled" : ""}><select data-d="${i}" data-field="yes" aria-label="${d.name} 模拟判定" ${!d.on ? "disabled" : ""}><option value="yes" ${d.yes ? "selected" : ""}>阳性</option><option value="no" ${!d.yes ? "selected" : ""}>未支持</option></select></div>`,
    )
    .join("");
}
function score() {
  const active = detectors.filter((d) => d.on),
    sum = active.reduce((n, d) => n + d.w, 0),
    yes = active.filter((d) => d.yes),
    support = yes.reduce((n, d) => n + d.w, 0),
    ratio = sum > 0 ? support / sum : 0;
  const method = $("method").value as ConsensusMethod;
  let call =
    method === "weighted_vote"
      ? sum > 0 && ratio >= 0.5
      : method === "majority_vote"
        ? yes.length > active.length / 2
        : method === "intersection"
          ? yes.length === active.length
          : detectors[0].yes;
  return { active, sum, yes, support, ratio, method, call };
}
function renderScore() {
  const s = score();
  $("equation").innerHTML =
    `S = ${s.support.toFixed(2)} / ${s.sum.toFixed(2)} = ${s.sum ? s.ratio.toFixed(2) : "未定义"}<small>阳性支持权重 / 参与工具总权重 · 下方柱条始终显示加权得分</small>`;
  $("score-fill").style.width = s.ratio * 100 + "%";
  $("consensus-result").textContent = s.call
    ? "→ 规则判定：候选质粒"
    : "→ 规则判定：未通过";
  $("consensus-result").style.color = s.call ? "var(--teal)" : "var(--gold)";
  const rule = {
    weighted_vote: "加权规则：支持权重比例 ≥ 0.5；总权重为零时不通过。",
    majority_vote: "严格多数：阳性数 > 参与工具数 / 2；平票不通过。",
    intersection: "交集：所有参与检测器均为阳性。",
    single_tool: "仅 geNomad：忽略其他检测器的判定。",
  }[s.method];
  $("consensus-note").textContent =
    rule +
    " " +
    (s.active.length === 1
      ? "当前只有一个检测器，不构成多工具交叉支持。"
      : `当前 ${s.yes.length}/${s.active.length} 个检测器支持。`) +
    (s.active.length === 4 &&
    detectors[0].w === 0.6 &&
    detectors.slice(1).every((d, i) => d.w === [0.15, 0.15, 0.1][i])
      ? " 默认权重下，geNomad 单独阳性即可通过加权规则。"
      : "");
}
$("detectors").addEventListener("input", (e) => {
  const el = e.target;
  if (
    !(el instanceof HTMLInputElement || el instanceof HTMLSelectElement) ||
    !el.dataset.field
  )
    return;
  const d = detectors[Number(el.dataset.d)];
  if (el.dataset.field === "on" && el instanceof HTMLInputElement) {
    d.on = el.checked;
    detectorRows();
    document
      .querySelector<HTMLInputElement>(`#row-${d.id} input[type=checkbox]`)
      ?.focus();
  } else if (el.dataset.field === "w") {
    d.w = Math.max(0, Math.min(10, Number(el.value) || 0));
  } else {
    d.yes = el.value === "yes";
  }
  renderScore();
});
$("detectors").addEventListener("change", (e) => {
  const el = e.target;
  if (!(el instanceof HTMLInputElement)) return;
  if (el.dataset.field === "w") {
    el.value = String(detectors[Number(el.dataset.d)].w);
    renderScore();
  }
});
$("method").onchange = renderScore;
$("disagreement").onclick = () => {
  detectors.forEach((d, i) => {
    d.on = true;
    d.yes = i === 0;
    d.w = [0.6, 0.15, 0.15, 0.1][i];
  });
  $("method").value = "weighted_vote";
  detectorRows();
  renderScore();
};

let toastTimer: ReturnType<typeof setTimeout> | undefined;
function notifyUser(text: string) {
  clearTimeout(toastTimer);
  $("toast").textContent = text;
  $("toast").hidden = false;
  toastTimer = setTimeout(() => {
    $("toast").hidden = true;
  }, 4500);
}
$("copy-command").onclick = async () => {
  try {
    await navigator.clipboard.writeText(commandText());
    notifyUser("已复制示例命令；请替换样本表与数据库路径。");
  } catch {
    const range = document.createRange();
    range.selectNodeContents($("command"));
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
    notifyUser("命令已选中，请使用 Ctrl+C 或系统复制操作。");
  }
};
function descriptionText() {
  return [
    "# AutoPlasm · Nextflow 流程设计",
    "",
    `平台：${platforms[state.platform].label}`,
    `导出时间：${new Date().toISOString()}`,
    "通用五平台演示，文档校订于 2026-10-31；完整 protocol 路线见 platform-workflows.md，演示不代表真实运行结果。",
    "",
    ...stages().flatMap((c) => [
      "## " + c.id + " · " + c.name,
      "",
      c.text,
      "输入：" + c.input,
      "方法：" + c.method,
      "产物：" + c.output,
      "参数：" + c.param,
      "目录：" + c.path,
      "说明：" + c.note,
      "源码：" + c.source,
      "",
    ]),
    "## 当前演示开关",
    ...(["binning", "mag", "linking", "network"] as const).map(
      (id) =>
        "- " +
        id +
        ": " +
        ($(id).checked && !$(id).disabled ? "开启" : "关闭 / 当前平台不可用"),
    ),
    "",
    "## 示例命令",
    "数据库和样本路径必须替换；示例不证明环境就绪。",
    "```bash",
    commandText(),
    "```",
    "",
    "## 实现边界",
    "见 docs/fact-reliability-audit.md 与 docs/analysis-framework-plan.md。",
  ].join("\n");
}
$("export").onclick = () => {
  const blob = new Blob(["\ufeff" + descriptionText()], {
      type: "text/markdown;charset=utf-8",
    }),
    url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = "AutoPlasm-nextflow-" + state.platform + ".md";
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  notifyUser("已请求导出当前平台的流程说明。");
};
$("print").onclick = () => {
  stopPlay();
  window.print();
};
let motionOff = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
function setMotion() {
  document.body.classList.toggle("motion-off", motionOff);
  document.documentElement.style.scrollBehavior = motionOff ? "auto" : "";
  $("motion").textContent = motionOff ? "动画已暂停" : "暂停动画";
  $("motion").setAttribute("aria-pressed", String(motionOff));
}
$("motion").onclick = () => {
  motionOff = !motionOff;
  setMotion();
  if (motionOff) stopPlay();
};
renderPlatform();
detectorRows();
renderScore();
setMotion();
