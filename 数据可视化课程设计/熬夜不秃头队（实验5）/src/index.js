// ===== 全局配置 =====
const COLORS = {
    primary: "#00d4ff",
    secondary: "#7c3aed",
    tertiary: "#f59e0b",
    danger: "#ef4444",
    success: "#10b981",
    pink: "#ec4899",
    bg: "#0a0e1a",
    text: "#f0f4f8"
};

let healthData = [];
let behaviorData = [];
let socialData = [];
let globalData = [];
let filteredHealthData = [];
let worldGeoData = null;
let worldRotation = [0, -10];

const tooltip = d3.select("#tooltip");

// ===== 初始化星空背景 =====
function createStars() {
    const starsContainer = d3.select("#stars");
    for (let i = 0; i < 100; i++) {
        starsContainer.append("div")
            .attr("class", "star")
            .style("left", Math.random() * 100 + "%")
            .style("top", Math.random() * 100 + "%")
            .style("width", (Math.random() * 2 + 1) + "px")
            .style("height", (Math.random() * 2 + 1) + "px")
            .style("animation-delay", Math.random() * 3 + "s");
    }
}

// ===== 数据加载 =====
Promise.all([
    d3.csv("Sleep_health_and_lifestyle_dataset.csv"),
    d3.csv("late_night_behavior.csv"),
    d3.csv("social_media_sleep_impact.csv"),
    d3.csv("global_sleep_stats.csv")
]).then(([health, behavior, social, global]) => {
    
    // 处理健康数据
    const BMI_MAP = { "Normal Weight": "正常", "Normal": "正常", "Overweight": "超重", "Obese": "肥胖" };
    const DISORDER_MAP = { "None": "无睡眠障碍", "No Disorder": "无睡眠障碍", "Sleep Apnea": "睡眠呼吸暂停", "Insomnia": "失眠" };

    healthData = health.map(d => ({
        id: d['Person ID'],
        gender: d.Gender,
        age: +d.Age,
        occupation: d.Occupation,
        sleepDuration: +d['Sleep Duration'],
        sleepQuality: +d['Quality of Sleep'],
        activityLevel: +d['Physical Activity Level'],
        stressLevel: +d['Stress Level'],
        bmi: BMI_MAP[d['BMI Category']] || BMI_MAP[d['BMI Category']?.trim()] || d['BMI Category'],
        heartRate: +d['Heart Rate'],
        steps: +d['Daily Steps'],
        disorder: DISORDER_MAP[d['Sleep Disorder']] || DISORDER_MAP[d['Sleep Disorder']?.trim()] || d['Sleep Disorder']
    }));

    // 处理熬夜行为数据
    behaviorData = behavior.map(d => ({
        hour: +d.hour,
        dayType: d.day_type,
        socialMedia: +d.social_media,
        gaming: +d.gaming,
        workStudy: +d.work_study,
        videoStreaming: +d.video_streaming,
        browsing: +d.browsing,
        caffeine: +d.caffeine_consumed,
        peopleCount: +d.people_count
    }));

    // 处理社交媒体数据
    socialData = social.map(d => ({
        ageGroup: d.age_group,
        platform: d.platform,
        dailyHours: +d.daily_hours,
        lateNightUsage: +d.late_night_usage,
        sleepQuality: +d.sleep_quality_score,
        addiction: +d.addiction_level,
        avgSleep: +d.avg_sleep_hours
    }));

    // 处理全球数据
    globalData = global.map(d => ({
        country: d.country,
        region: d.region,
        avgSleep: +d.avg_sleep_hours,
        lateNightRate: +d.late_night_rate,
        workHours: +d.work_hours_per_week,
        stressLevel: +d.stress_level,
        internetHours: +d.internet_hours,
        disorderRate: +d.sleep_disorder_rate
    }));

    d3.select("#loader").style("display", "none");
    createStars();
    initializeApp();

}).catch(err => {
    console.error("数据加载失败:", err);
    alert("数据加载失败！请检查CSV文件是否存在。");
});

// ===== 初始化应用 =====
function initializeApp() {
    filteredHealthData = healthData;
    
    // 初始化导航
    d3.selectAll(".nav-tab").on("click", function() {
        const page = this.dataset.page;
        d3.selectAll(".nav-tab").classed("active", false);
        d3.select(this).classed("active", true);
        d3.selectAll(".page-section").classed("active", false);
        d3.select(`#page-${page}`).classed("active", true);
        
        // 根据页面初始化相应图表
        if (page === "overview") {
            setTimeout(() => initOverviewPage(), 100);
        } else if (page === "behavior") {
            setTimeout(() => initBehaviorPage(), 100);
        } else if (page === "health") {
            setTimeout(() => initHealthPage(), 100);
        } else if (page === "global") {
            setTimeout(() => initGlobalPage(), 100);
        }
    });

    // 初始化第一页
    initOverviewPage();
}

// ===== 第一页：总览 =====
function initOverviewPage() {
    updateKPIs();
    initOccupationFilter();
    drawScatter();
    drawRadar(null);
    drawStackedBar();
    drawStressSleepChart();
}

function updateKPIs() {
    const data = filteredHealthData;
    const disorderRate = (data.filter(d => d.disorder !== "无睡眠障碍").length / data.length * 100).toFixed(1);
    
    d3.select("#kpi-total").text(data.length);
    d3.select("#kpi-sleep").text(d3.mean(data, d => d.sleepDuration).toFixed(1));
    d3.select("#kpi-stress").text(d3.mean(data, d => d.stressLevel).toFixed(1));
    d3.select("#kpi-steps").text(d3.format(",")(Math.round(d3.mean(data, d => d.steps))));
    d3.select("#kpi-disorder").text(disorderRate);
}

function initOccupationFilter() {
    const occupations = Array.from(new Set(healthData.map(d => d.occupation))).sort();
    const select = d3.select("#occupationFilter");
    select.selectAll("option:not(:first-child)").remove();
    
    occupations.forEach(occ => {
        select.append("option").attr("value", occ).text(occ);
    });

    select.on("change", function() {
        const value = this.value;
        filteredHealthData = value === "all" ? healthData : healthData.filter(d => d.occupation === value);
        updateKPIs();
        drawScatter();
        drawRadar(null);
        drawStackedBar();
        drawStressSleepChart();
    });
}

// 气泡散点图
function drawScatter() {
    const container = d3.select("#scatter-chart");
    container.selectAll("*").remove();
    
    const containerWidth = container.node().getBoundingClientRect().width;
    const containerHeight = container.node().getBoundingClientRect().height;
    const margin = {top: 20, right: 20, bottom: 60, left: 60};
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    const svg = container.append("svg")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear()
        .domain([20, 100])
        .range([0, width]);

    const y = d3.scaleLinear()
        .domain([3, 10])
        .range([height, 0]);

    const color = d3.scaleOrdinal()
        .domain(["正常", "超重", "肥胖"])
        .range([COLORS.success, COLORS.tertiary, COLORS.danger]);

    // 添加网格线
    svg.append("g")
        .attr("class", "grid")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(x).tickSize(-height).tickFormat(""))
        .style("stroke-opacity", 0.1);

    svg.append("g")
        .attr("class", "grid")
        .call(d3.axisLeft(y).tickSize(-width).tickFormat(""))
        .style("stroke-opacity", 0.1);

    svg.append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(x))
        .attr("class", "axis");

    svg.append("g")
        .call(d3.axisLeft(y))
        .attr("class", "axis");

    svg.append("text")
        .attr("x", width / 2)
        .attr("y", height + 45)
        .attr("fill", COLORS.text)
        .style("text-anchor", "middle")
        .style("font-size", "12px")
        .text("运动量 (分钟/天)");

    svg.append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", -45)
        .attr("x", -height / 2)
        .attr("fill", COLORS.text)
        .style("text-anchor", "middle")
        .style("font-size", "12px")
        .text("睡眠质量 (1-10)");

    svg.selectAll("circle")
        .data(filteredHealthData)
        .join("circle")
        .attr("cx", d => x(d.activityLevel))
        .attr("cy", d => y(d.sleepQuality))
        .attr("r", 0) // 初始半径为0
        .style("fill", d => color(d.bmi))
        .style("opacity", 0) // 初始透明度为0
        .style("stroke", "#fff")
        .style("stroke-width", 0.5)
        .transition() // 添加过渡动画
        .duration(800)
        .delay((d, i) => Math.random() * 500) // 随机延迟，产生闪烁出现的效果
        .attr("r", d => d.sleepDuration * 1.5)
        .style("opacity", 0.6);
        
    // 重新绑定交互事件（注意：过渡后的对象需要重新选择或在过渡前绑定，这里在过渡后绑定会有问题吗？
    // D3 transition返回的是transition对象，无法直接on。应该在join后直接on，attr放在transition里。
    
    svg.selectAll("circle") // 重新选择以绑定事件
        .on("mouseover", (event, d) => {
            showTooltip(event, `
                <div class="tooltip-title">${d.occupation}</div>
                <div class="tooltip-row">
                    <span>性别/年龄:</span>
                    <span>${d.gender}, ${d.age}岁</span>
                </div>
                <div class="tooltip-row">
                    <span>BMI:</span>
                    <span>${d.bmi}</span>
                </div>
                <div class="tooltip-row">
                    <span>睡眠时长:</span>
                    <span>${d.sleepDuration}小时</span>
                </div>
                <div class="tooltip-row">
                    <span>睡眠质量:</span>
                    <span>${d.sleepQuality}/10</span>
                </div>
                <div class="tooltip-row">
                    <span>日均步数:</span>
                    <span>${d3.format(",")(d.steps)}</span>
                </div>
            `);
            d3.select(event.currentTarget)
                .transition()
                .duration(200)
                .style("opacity", 1)
                .style("stroke-width", 2);
            
            drawRadar(d);
        })
        .on("mouseout", (event, d) => {
            hideTooltip();
            d3.select(event.currentTarget)
                .transition()
                .duration(200)
                .style("opacity", 0.6)
                .style("stroke-width", 0.5);
            
            drawRadar(null);
        });

    // 图例
    const legend = d3.select("#scatter-legend");
    legend.html("");
    ["正常", "超重", "肥胖"].forEach(bmi => {
        const item = legend.append("div").attr("class", "legend-item");
        item.append("div")
            .attr("class", "legend-color")
            .style("background", color(bmi));
        item.append("span").text(bmi);
    });
}

// 雷达图
function drawRadar(userData) {
    const container = d3.select("#radar-chart");
    container.selectAll("*").remove();

    const containerWidth = container.node().getBoundingClientRect().width;
    const containerHeight = container.node().getBoundingClientRect().height;
    const radius = Math.min(containerWidth, containerHeight) / 2 - 40;

    const svg = container.append("svg")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .append("g")
        .attr("transform", `translate(${containerWidth/2},${containerHeight/2})`);

    const features = ["睡眠时长", "睡眠质量", "压力水平", "运动量", "心率健康"];
    const angleSlice = Math.PI * 2 / features.length;

    const normalize = (d) => ({
        "睡眠时长": (d.sleepDuration / 10) * 10,
        "睡眠质量": (d.sleepQuality / 10) * 10,
        "压力水平": (10 - d.stressLevel),
        "运动量": (d.activityLevel / 100) * 10,
        "心率健康": Math.max(0, Math.min(10, ((100 - Math.abs(d.heartRate - 70)) / 100) * 10))
    });

    // 计算平均值
    const avgData = {
        sleepDuration: d3.mean(filteredHealthData, d => d.sleepDuration),
        sleepQuality: d3.mean(filteredHealthData, d => d.sleepQuality),
        stressLevel: d3.mean(filteredHealthData, d => d.stressLevel),
        activityLevel: d3.mean(filteredHealthData, d => d.activityLevel),
        heartRate: d3.mean(filteredHealthData, d => d.heartRate)
    };

    const rScale = d3.scaleLinear().range([0, radius]).domain([0, 10]);

    // 绘制网格
    [2, 4, 6, 8, 10].forEach(level => {
        svg.append("circle")
            .attr("r", rScale(level))
            .style("fill", "none")
            .style("stroke", level === 10 ? "rgba(100, 140, 200, 0.5)" : "rgba(100, 140, 200, 0.3)")
            .style("stroke-dasharray", level === 10 ? "none" : "5,5")
            .style("stroke-width", level === 10 ? 2 : 1);
    });

    // 绘制轴线
    features.forEach((feature, i) => {
        const angle = angleSlice * i - Math.PI/2;
        const x = rScale(10) * Math.cos(angle);
        const y = rScale(10) * Math.sin(angle);
        
        svg.append("line")
            .attr("x1", 0).attr("y1", 0)
            .attr("x2", x).attr("y2", y)
            .style("stroke", "rgba(100, 140, 200, 0.3)");

        // 调整文字位置，睡眠时长（第一个）稍微靠近
        const distance = i === 0 ? 11.5 : 13;
        svg.append("text")
            .attr("x", rScale(distance) * Math.cos(angle))
            .attr("y", rScale(distance) * Math.sin(angle))
            .text(feature)
            .style("text-anchor", "middle")
            .style("font-size", "11px")
            .style("fill", COLORS.text);
    });

    const line = d3.lineRadial()
        .angle((d, i) => i * angleSlice)
        .radius(d => rScale(d))
        .curve(d3.curveLinearClosed);

    const lineZero = d3.lineRadial()
        .angle((d, i) => i * angleSlice)
        .radius(0)
        .curve(d3.curveLinearClosed);

    const normalizedAvg = features.map(f => normalize(avgData)[f]);

    svg.append("path")
        .datum(normalizedAvg)
        .attr("d", lineZero) // 初始形态：收缩在中心
        .style("fill", COLORS.primary)
        .style("fill-opacity", 0.2)
        .style("stroke", COLORS.primary)
        .style("stroke-width", 2)
        .transition() // 动画
        .duration(1000)
        .ease(d3.easeElasticOut.amplitude(1).period(0.8)) // 弹性效果
        .attr("d", line);

    if (userData) {
        const normalizedUser = features.map(f => normalize(userData)[f]);
        
        svg.append("path")
            .datum(normalizedUser)
            .attr("d", lineZero)
            .style("fill", "none")
            .style("stroke", "#fff")
            .style("stroke-width", 2.5)
            .transition()
            .duration(800)
            .ease(d3.easeCubicOut)
            .attr("d", line);
    }
}

// 桑基图 - BMI与睡眠障碍关系
function drawStackedBar() {
    const container = d3.select("#stacked-bar-chart");
    container.selectAll("*").remove();

    const containerWidth = container.node().getBoundingClientRect().width;
    const containerHeight = container.node().getBoundingClientRect().height;
    const margin = {top: 20, right: 60, bottom: 20, left: 15};
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    const svg = container.append("svg")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .style("overflow", "visible")
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // 准备桑基图数据
    const bmiCategories = ["正常", "超重", "肥胖"];
    const disorders = ["无睡眠障碍", "睡眠呼吸暂停", "失眠"];
    
    // 创建节点和链接
    const nodes = [];
    const links = [];
    
    // 添加BMI节点
    bmiCategories.forEach((bmi, i) => {
        nodes.push({ name: bmi, category: "bmi" });
    });
    
    // 添加睡眠障碍节点
    disorders.forEach((disorder, i) => {
        nodes.push({ name: disorder, category: "disorder" });
    });
    
    // 创建链接数据
    bmiCategories.forEach((bmi, i) => {
        disorders.forEach((disorder, j) => {
            const count = filteredHealthData.filter(d => d.bmi === bmi && d.disorder === disorder).length;
            if (count > 0) {
                links.push({
                    source: i,
                    target: bmiCategories.length + j,
                    value: count
                });
            }
        });
    });

    // 计算每个BMI节点的总人数和每个睡眠节点的总人数，用于分配最大可用厚度
    const sourceTotals = {};
    const targetTotals = {};
    links.forEach(link => {
        sourceTotals[link.source] = (sourceTotals[link.source] || 0) + link.value;
        targetTotals[link.target] = (targetTotals[link.target] || 0) + link.value;
    });

    // 设置节点位置
    const nodeWidth = 26;
    const nodePadding = 30;
    const leftX = 80;
    const rightX = width - 80;
    
    // 计算总人数用于归一化
    const totalPeople = filteredHealthData.length;
    
    // 手动布局节点
    const bmiNodeHeight = (height - (bmiCategories.length - 1) * nodePadding) / bmiCategories.length;
    const disorderNodeHeight = (height - (disorders.length - 1) * nodePadding) / disorders.length;
    
    nodes.forEach((node, i) => {
        if (node.category === "bmi") {
            const index = i;
            node.x0 = leftX;
            node.x1 = leftX + nodeWidth;
            node.y0 = index * (bmiNodeHeight + nodePadding);
            node.y1 = node.y0 + bmiNodeHeight;
        } else {
            const index = i - bmiCategories.length;
            node.x0 = rightX;
            node.x1 = rightX + nodeWidth;
            node.y0 = index * (disorderNodeHeight + nodePadding);
            node.y1 = node.y0 + disorderNodeHeight;
        }
    });

    // 颜色映射
    const bmiColors = {
        "正常": COLORS.success,
        "超重": COLORS.tertiary,
        "肥胖": COLORS.danger
    };
    
    const disorderColors = {
        "无睡眠障碍": COLORS.primary,
        "睡眠呼吸暂停": COLORS.secondary,
        "失眠": COLORS.pink
    };

    // 绘制链接（流）
    const linkGroup = svg.append("g").attr("class", "links");

    links.forEach((link, i) => {
        const sourceNode = nodes[link.source];
        const targetNode = nodes[link.target];
        
        const availableHeight = Math.min(sourceNode.y1 - sourceNode.y0, targetNode.y1 - targetNode.y0) * 0.8;
        const scaleBase = Math.max(sourceTotals[link.source], targetTotals[link.target]);
        const linkHeight = availableHeight * (link.value / scaleBase);
        
        const x0 = sourceNode.x1;
        const x1 = targetNode.x0;
        const y0 = sourceNode.y0 + (sourceNode.y1 - sourceNode.y0) / 2;
        const y1 = targetNode.y0 + (targetNode.y1 - targetNode.y0) / 2;
        const xi = d3.interpolateNumber(x0, x1);
        const x2 = xi(0.5);

        const path = linkGroup.append("path")
            .attr("d", `M ${x0} ${y0 - linkHeight/2}
                        C ${x2} ${y0 - linkHeight/2},
                          ${x2} ${y1 - linkHeight/2},
                          ${x1} ${y1 - linkHeight/2}
                        L ${x1} ${y1 + linkHeight/2}
                        C ${x2} ${y1 + linkHeight/2},
                          ${x2} ${y0 + linkHeight/2},
                          ${x0} ${y0 + linkHeight/2}
                        Z`)
            .style("fill", bmiColors[sourceNode.name])
            .style("opacity", 0)
            .style("stroke", "none");

        // 动画
        path.transition()
            .duration(800)
            .delay(i * 50)
            .style("opacity", 0.3);

        // 事件
        path.on("mouseover", function(event) {
            d3.select(this)
                .style("opacity", 0.6)
                .style("stroke", bmiColors[sourceNode.name])
                .style("stroke-width", 1);
            
            showTooltip(event, `
                <div class="tooltip-title">${sourceNode.name} → ${targetNode.name}</div>
                <div class="tooltip-row">
                    <span>人数:</span>
                    <span>${link.value} 人</span>
                </div>
                <div class="tooltip-row">
                    <span>占比:</span>
                    <span>${(link.value / totalPeople * 100).toFixed(1)}%</span>
                </div>
            `);
        })
        .on("mouseout", function() {
            d3.select(this)
                .style("opacity", 0.3)
                .style("stroke", "none");
            hideTooltip();
        });
    });

    // 绘制节点
    const nodeGroup = svg.append("g").attr("class", "nodes");
    
    nodes.forEach((node, i) => {
        const g = nodeGroup.append("g");
        
        // 绘制节点矩形
        g.append("rect")
            .attr("x", node.x0)
            .attr("y", node.y0 + (node.y1 - node.y0)/2) // 初始位置在中心
            .attr("width", nodeWidth)
            .attr("height", 0) // 初始高度为0
            .style("fill", node.category === "bmi" ? bmiColors[node.name] : disorderColors[node.name])
            .style("stroke", "#fff")
            .style("stroke-width", 2)
            .style("rx", 4)
            .transition() // 展开动画
            .duration(800)
            .delay(i * 100)
            .attr("y", node.y0)
            .attr("height", node.y1 - node.y0);
        
        // ... (标签代码保持不变，或者添加简单的淡入)
        // 使用g的opacity来控制文字和矩形的一起淡入也可以，但矩形展开更酷。
        // 文字延迟显示
        const labelX = node.category === "bmi" ? node.x0 - 10 : node.x1 + 10;
        const textAnchor = node.category === "bmi" ? "end" : "start";
        
        g.append("text")
            .attr("x", labelX)
            .attr("y", (node.y0 + node.y1) / 2)
            .attr("dy", "0.35em")
            .attr("text-anchor", textAnchor)
            .style("fill", COLORS.text)
            .style("font-size", "12px")
            .style("font-weight", "600")
            .style("opacity", 0)
            .text(node.name)
            .transition().duration(800).delay(500 + i*100).style("opacity", 1);
        
        // 添加节点数值
        const count = node.category === "bmi" 
            ? filteredHealthData.filter(d => d.bmi === node.name).length
            : filteredHealthData.filter(d => d.disorder === node.name).length;
        
        g.append("text")
            .attr("x", labelX)
            .attr("y", (node.y0 + node.y1) / 2 + 16)
            .attr("dy", "0.35em")
            .attr("text-anchor", textAnchor)
            .style("fill", COLORS.text)
            .style("font-size", "10px")
            .style("opacity", 0)
            .text(`${count}人`)
            .transition().duration(800).delay(600 + i*100).style("opacity", 0.7);
    });

    // 添加标题
    svg.append("text")
        .attr("x", leftX + nodeWidth / 2)
        .attr("y", -5)
        .attr("text-anchor", "middle")
        .style("fill", COLORS.text)
        .style("font-size", "11px")
        .style("opacity", 0.8)
        .text("BMI分类");
    
    svg.append("text")
        .attr("x", rightX + nodeWidth / 2)
        .attr("y", -5)
        .attr("text-anchor", "middle")
        .style("fill", COLORS.text)
        .style("font-size", "11px")
        .style("opacity", 0.8)
        .text("睡眠状况");
}

// 环形图
function drawStressSleepChart() {
    const container = d3.select("#stress-sleep-chart");
    container.selectAll("*").remove();

    const data = filteredHealthData;
    const containerWidth = container.node().getBoundingClientRect().width;
    const containerHeight = container.node().getBoundingClientRect().height;
    const margin = {top: 30, right: 80, bottom: 50, left: 60};
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    const svg = container.append("svg")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // 1. 定义比例尺
    const x = d3.scaleLinear()
        .domain([d3.min(data, d => d.sleepDuration) - 0.5, d3.max(data, d => d.sleepDuration) + 0.5])
        .range([0, width]);

    const y = d3.scaleLinear()
        .domain([0, 10])
        .range([height, 0]);

    // 2. 计算密度等高线
    const densityData = d3.contourDensity()
        .x(d => x(d.sleepDuration))
        .y(d => y(d.stressLevel))
        .size([width, height])
        .bandwidth(25) // 平滑度
        .thresholds(20) // 层级数量
        (data);

    // 3. 颜色比例尺 (Turbo 适合热力图)
    const color = d3.scaleSequential(d3.interpolateTurbo)
        .domain([0, d3.max(densityData, d => d.value)]);

    // 4. 绘制背景网格
    svg.append("g")
        .attr("class", "grid")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(x).tickSize(-height).tickFormat(""))
        .style("stroke-opacity", 0.1);

    svg.append("g")
        .attr("class", "grid")
        .call(d3.axisLeft(y).tickSize(-width).tickFormat(""))
        .style("stroke-opacity", 0.1);

    // 5. 绘制等高线路径
    svg.append("g")
        .selectAll("path")
        .data(densityData)
        .enter().append("path")
        .attr("d", d3.geoPath())
        .attr("fill", d => color(d.value))
        .attr("stroke", "none")
        .style("opacity", 0) // 初始透明
        .transition() // 渐入
        .duration(1000)
        .delay((d, i) => i * 20)
        .style("opacity", 0.8);

    // 6. 添加散点 (低透明度，用于展示具体分布)
    svg.selectAll("circle")
        .data(data)
        .enter().append("circle")
        .attr("cx", d => x(d.sleepDuration))
        .attr("cy", d => y(d.stressLevel))
        .attr("r", 0) // 初始半径0
        .style("fill", "#fff")
        .style("opacity", 0)
        .style("pointer-events", "none") // 不干扰交互
        .transition()
        .duration(800)
        .delay((d, i) => Math.random() * 800)
        .attr("r", 2)
        .style("opacity", 0.2);

    // 7. 坐标轴
    svg.append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(x))
        .attr("class", "axis")
        .style("font-size", "12px");

    svg.append("g")
        .call(d3.axisLeft(y))
        .attr("class", "axis")
        .style("font-size", "12px");

    // 8. 轴标签
    svg.append("text")
        .attr("x", width / 2)
        .attr("y", height + 40)
        .attr("fill", COLORS.text)
        .style("text-anchor", "middle")
        .text("睡眠时长 (小时)");

    svg.append("text")
        .attr("transform", "rotate(-90)")
        .attr("y", -40)
        .attr("x", -height / 2)
        .attr("fill", COLORS.text)
        .style("text-anchor", "middle")
        .text("压力水平 (1-10)");

    // 9. 添加热力图图例
    const legendHeight = 150;
    const legendWidth = 15;
    
    const legendSvg = svg.append("g")
        .attr("transform", `translate(${width + 20}, ${(height - legendHeight) / 2})`);

    const defs = svg.append("defs");
    const linearGradient = defs.append("linearGradient")
        .attr("id", "linear-gradient")
        .attr("x1", "0%")
        .attr("y1", "100%")
        .attr("x2", "0%")
        .attr("y2", "0%");

    // 生成渐变色
    const numStops = 10;
    for (let i = 0; i <= numStops; i++) {
        const offset = i / numStops;
        linearGradient.append("stop")
            .attr("offset", `${offset * 100}%`)
            .attr("stop-color", d3.interpolateTurbo(offset));
    }

    legendSvg.append("rect")
        .attr("width", legendWidth)
        .attr("height", legendHeight)
        .style("fill", "url(#linear-gradient)")
        .style("stroke", "#ccc")
        .style("stroke-width", 0.5);

    // 图例标签
    legendSvg.append("text")
        .attr("x", legendWidth + 5)
        .attr("y", 10)
        .style("fill", COLORS.text)
        .style("font-size", "10px")
        .text("高密度");

    legendSvg.append("text")
        .attr("x", legendWidth + 5)
        .attr("y", legendHeight)
        .style("fill", COLORS.text)
        .style("font-size", "10px")
        .text("低密度");

    // 10. 添加"热点"标注 (找出密度最高的区域)
    if (densityData.length > 0) {
        // 简单地在图表上方添加说明
        svg.append("text")
            .attr("x", width - 10)
            .attr("y", 20)
            .attr("text-anchor", "end")
            .style("fill", COLORS.text)
            .style("font-size", "12px")
            .style("font-style", "italic")
            .text("颜色越暖表示人群越集中");
    }
}
// 已删除热力图
// 已删除饼图

// ===== 第二页：熬夜行为分析 =====
function initBehaviorPage() {
    drawStreamgraph();
    
    // 移除旧的按钮绑定
}

/* 
// 热力图 (已删除)
// 饼图 (已删除)
*/

// 河流图 (Streamgraph) - 深夜活动流量趋势
function drawStreamgraph() {
    const container = d3.select("#streamgraph-chart");
    if (container.empty()) return;
    container.selectAll("*").remove();

    if (!behaviorData || behaviorData.length === 0) return;

    let containerWidth = container.node().getBoundingClientRect().width;
    let containerHeight = container.node().getBoundingClientRect().height;
    if (!containerWidth) containerWidth = container.node().clientWidth || 500;
    if (!containerHeight) containerHeight = container.node().clientHeight || 300;

    const margin = {top: 20, right: 30, bottom: 30, left: 30};
    const width = Math.max(0, containerWidth - margin.left - margin.right);
    const height = Math.max(0, containerHeight - margin.top - margin.bottom);

    const svg = container.append("svg")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // 1. 数据预处理
    const keys = ["socialMedia", "gaming", "workStudy", "videoStreaming", "browsing"];
    const keyLabels = {
        "socialMedia": "社交媒体",
        "gaming": "游戏",
        "workStudy": "工作学习",
        "videoStreaming": "视频",
        "browsing": "浏览"
    };

    const hours = [22, 23, 0, 1, 2, 3];
    const groupedData = hours.map(h => {
        const hourRecords = behaviorData.filter(d => d.hour === h);
        const obj = { hour: h, displayTime: h + ":00" };
        keys.forEach(k => {
            obj[k] = d3.sum(hourRecords, d => d[k]);
        });
        return obj;
    });

    // 2. 堆叠配置
    // 使用 stackOrderNone 来保持图层顺序与 keys 一致
    const stack = d3.stack()
        .keys(keys)
        .offset(d3.stackOffsetSilhouette)
        .order(d3.stackOrderNone);

    const series = stack(groupedData);

    // 3. 比例尺
    const x = d3.scalePoint()
        .domain(hours.map(h => h + ":00"))
        .range([0, width]);

    // Y轴范围
    const yMin = d3.min(series, layer => d3.min(layer, d => d[0]));
    const yMax = d3.max(series, layer => d3.max(layer, d => d[1]));

    const y = d3.scaleLinear()
        .domain([yMin, yMax])
        .range([height, 0]);

    // 颜色映射
    const z = d3.scaleOrdinal()
        .domain(keys)
        .range([COLORS.primary, COLORS.secondary, COLORS.tertiary, COLORS.pink, COLORS.success]);

    // 4. 区域生成器
    const area = d3.area()
        .x(d => x(d.data.displayTime))
        .y0(d => y(d[0]))
        .y1(d => y(d[1]))
        .curve(d3.curveBasis);

    const areaZero = d3.area()
        .x(d => x(d.data.displayTime))
        .y0(height) // 从底部升起，或者从中间展开
        .y1(height) // 这里尝试从底部升起的效果，或者y(d[0]) (如果不offsetSilhouette)
         // 对于Silhouette，中心对称，最好是从中心展开。
         // 我们简单点，用 opacity 淡入 + mask 效果，或者用 flat line at center
         .y0(height/2)
         .y1(height/2)
        .curve(d3.curveBasis);

    // 5. 交互状态
    let selectedKey = null;

    // 6. 绘制路径
    svg.selectAll("path")
        .data(series)
        .join("path")
        .attr("d", areaZero) // 初始：扁平
        .style("fill", d => z(d.key))
        .style("opacity", 0)
        .style("cursor", "crosshair")
        .transition() // 动画
        .duration(1200)
        .delay((d, i) => i * 100)
        .ease(d3.easeCubicOut)
        .attr("d", area)
        .style("opacity", 0.9);
        
    // 重新选择路径以绑定事件
    const paths = svg.selectAll("path");

    // 7. 添加垂直指示线
    const verticalLine = svg.append("line")
        .attr("stroke", "rgba(255,255,255,0.5)")
        .attr("stroke-width", 1)
        .attr("stroke-dasharray", "4 4")
        .style("opacity", 0)
        .style("pointer-events", "none");

    const timeLabel = svg.append("text")
        .attr("y", height + 20) 
        .attr("text-anchor", "middle")
        .style("fill", COLORS.text)
        .style("font-size", "12px")
        .style("opacity", 0);

    // 8. 交互事件层 (覆盖全图)
    svg.append("rect")
        .attr("width", width)
        .attr("height", height)
        .style("fill", "transparent")
        .on("mousemove", function(event) {
            const [mouseX] = d3.pointer(event);
            
            // 找到最近的时间点
            const step = width / (hours.length - 1);
            const index = Math.round(mouseX / step);
            const safeIndex = Math.max(0, Math.min(index, hours.length - 1));
            const currentHourObj = groupedData[safeIndex];
            const currentX = x(currentHourObj.displayTime);

            // 更新指示线
            verticalLine
                .attr("x1", currentX)
                .attr("x2", currentX)
                .attr("y1", 0)
                .attr("y2", height)
                .style("opacity", 1);
            
            timeLabel
                .attr("x", currentX)
                .text(currentHourObj.displayTime)
                .style("opacity", 1);

            // 确定当前鼠标下的区域 (大致反推)
            // 更简便的方法：直接查看堆叠数据中在当前索引的值
            // 但这还需要判断Y轴。
            // 优化方案：直接遍历series，看哪一个的y0/y1区间包含了mouseY
            const [_, mouseY] = d3.pointer(event);
            
            let hoveredKey = null;
            let hoveredValue = 0;

            // 遍历所有层来检测鼠标在哪个层内
            // 由于曲线是curveBasis，Y值与数据点Y值不完全一致，这里用近似判断
            // 或者：直接显示该时间点所有类型的数值列表
            
            let tooltipHtml = `<div class="tooltip-title">${currentHourObj.displayTime}</div>`;
            
            // 为了让 Tooltip 与图例和视觉上从上到下的顺序一致
            // 由于 stackOrderNone 绘制是 index 0 在最底，index N 在最顶
            // 如果我们视觉上看（假设Silhouette是从中线往上下扩），通常最后的元素可能在最上面或最下面取决于具体偏移
            // 但一般逻辑上，为了匹配图例（图例通常是上到下列表），我们倒序遍历 keys 显示
            const reversedSeries = [...series].reverse();
            
            reversedSeries.forEach(s => {
                const key = s.key;
                const val = currentHourObj[key]; // 原始值
                // 高亮逻辑
                if (selectedKey && key !== selectedKey) return;
                
                tooltipHtml += `
                <div class="tooltip-row" style="color: ${z(key)}; margin-bottom: 2px;">
                    <span style="display:inline-block;width:8px;height:8px;background:${z(key)};margin-right:5px;border-radius:2px;"></span>
                    <span>${keyLabels[key]}:</span>
                    <span style="font-weight:bold;margin-left:auto;">${val}</span>
                </div>`;
            });

            // 尝试判断具体hover的是哪个
            // 简单逻辑：如果用户点击了某个色块，就锁定它。
            
            showTooltip(event, tooltipHtml);
        })
        .on("mouseout", function() {
            verticalLine.style("opacity", 0);
            timeLabel.style("opacity", 0);
            hideTooltip();
        })
        .on("click", function(event) {
             // 简单的点击切换：无 -> 有 -> 无
             // 这里其实不需要复杂的点击逻辑，因为mousemove已经显示了该列所有数据
             // 我们可以做一个 "冻结 tooltip" 的功能，或者什么都不做
        });
        
    // 9. 单独给路径加点击，用于高亮某个类别
    paths.on("click", function(event, d) {
        event.stopPropagation(); // 阻止冒泡到背景rect
        if (selectedKey === d.key) {
            selectedKey = null; // 取消选择
            paths.style("opacity", 0.9).style("stroke", "none");
        } else {
            selectedKey = d.key;
            paths.style("opacity", 0.2); // 其他变淡
            d3.select(this).style("opacity", 1).style("stroke", "#fff").style("stroke-width", 1);
        }
    });

    // 10. 添加X轴
    const xAxis = svg.append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(x).tickSize(0).tickPadding(10));
        
    xAxis.select(".domain").remove();

    xAxis.selectAll(".tick text")
        .style("fill", COLORS.text)
        .style("font-size", "11px");

    // X轴淡入
    xAxis.style("opacity", 0)
        .transition()
        .duration(1000)
        .delay(1200)
        .style("opacity", 1)
        .on("end", () => console.log("X轴动画完成"));

    // 11. 图例
    const legend = svg.append("g")
        .attr("transform", `translate(${width - 80}, 0)`);
        
    // 倒序遍历 keys 以匹配从上到下的视觉顺序
    [...keys].reverse().forEach((key, i) => {
        const g = legend.append("g")
            .attr("transform", `translate(0, ${i * 15})`);
            
        g.append("rect")
            .attr("width", 8)
            .attr("height", 8)
            .attr("rx", 2)
            .style("fill", z(key));
            
        g.append("text")
            .attr("x", 12)
            .attr("y", 8)
            .text(keyLabels[key])
            .style("fill", "rgba(255,255,255,0.7)")
            .style("font-size", "10px")
            .style("alignment-baseline", "middle");
    });
    
    // 图例淡入
    legend.style("opacity", 0)
        .transition()
        .duration(1000)
        .delay(1200)
        .style("opacity", 1)
        .on("end", () => console.log("图例动画完成"));
}

// ===== 工具函数 =====
function showTooltip(event, html) {
    tooltip.style("opacity", 1).html(html);
    
    // 使用 clientX/clientY 因为 tooltip 使用 position: fixed
    let x = event.clientX + 15;
    let y = event.clientY - 15;
    
    // 获取提示框尺寸
    const tooltipNode = tooltip.node();
    const tooltipRect = tooltipNode.getBoundingClientRect();
    const tooltipWidth = tooltipRect.width;
    const tooltipHeight = tooltipRect.height;
    
    // 边界检测 - 防止超出右边界
    if (x + tooltipWidth > window.innerWidth) {
        x = event.clientX - tooltipWidth - 15;
    }
    
    // 边界检测 - 防止超出底部边界
    if (y + tooltipHeight > window.innerHeight) {
        y = event.clientY - tooltipHeight - 15;
    }
    
    // 边界检测 - 防止超出左边界
    if (x < 0) {
        x = 15;
    }
    
    // 边界检测 - 防止超出顶部边界
    if (y < 0) {
        y = 15;
    }
    
    tooltip.style("left", x + "px").style("top", y + "px");
}

function hideTooltip() {
    tooltip.style("opacity", 0);
}

// 窗口调整
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        const activePage = d3.select(".page-section.active").attr("id");
        if (activePage === "page-overview") {
            drawScatter();
            drawRadar(null);
            drawStackedBar();
            drawStressSleepChart();
        } else if (activePage === "page-behavior") {
            drawStreamgraph();
        } else if (activePage === "page-health") {
            const ageGroups = ["18-24", "25-34", "35-44", "45+", "all"];
            const sliderValue = d3.select('#ageGroupSlider').node()?.value || 0;
            const activeAge = ageGroups[sliderValue];
            drawParallelCoords(activeAge);
            drawAddiction();
        } else if (activePage === "page-global") {
            drawWorldMap();
            drawGlobalRanking();
        }
    }, 500); // 增加延时以确保容器渲染
});

// ===== 第三页：健康影响分析 =====
function initHealthPage() {
    drawParallelCoords("18-24");
    drawAddiction();
    
    // 初始化年龄段滑块
    const ageGroups = [
        { value: "18-24", label: "18-24岁" },
        { value: "25-34", label: "25-34岁" },
        { value: "35-44", label: "35-44岁" },
        { value: "45+", label: "45岁以上" },
        { value: "all", label: "所有年龄段" }
    ];
    
    // 创建滑块标记
    const markersContainer = d3.select("#ageSliderMarkers");
    markersContainer.selectAll("*").remove(); // 清空之前的标记
    ageGroups.forEach((group, i) => {
        markersContainer.append("div")
            .style("text-align", "center")
            .style("flex", "1")
            .style("transition", "all 0.2s")
            .attr("class", `age-marker age-marker-${i}`)
            .text(i === 4 ? "全部" : group.label.replace("岁", ""));
    });
    
    // 绑定滑块事件
    const slider = d3.select("#ageGroupSlider");
    const label = d3.select("#ageSliderLabel");
    
    slider.on("input", function() {
        const index = +this.value;
        const selectedGroup = ageGroups[index];
        label.text(selectedGroup.label);
        
        // 高亮当前选中的标记
        d3.selectAll(".age-marker")
            .style("color", "var(--text-muted)")
            .style("font-weight", "400")
            .style("transform", "scale(1)");
        d3.select(`.age-marker-${index}`)
            .style("color", "var(--accent)")
            .style("font-weight", "700")
            .style("transform", "scale(1.15)");
        
        drawParallelCoords(selectedGroup.value);
    });
    
    // 初始化第一个标记为高亮
    d3.select(".age-marker-0")
        .style("color", "var(--accent)")
        .style("font-weight", "700")
        .style("transform", "scale(1.15)");
}

// 平行坐标图 - 多维睡眠影响因子溯源
function drawParallelCoords(filterAgeGroup) {
    const container = d3.select("#parallel-coords-chart");
    if (container.empty()) return;
    container.selectAll("*").remove();
    
    // 如果没有传入过滤年龄组，默认为第一组 "18-24" (因为初始化时滑块在0) 
    // 或者默认为 "all" 如果你想默认显示所有。
    // 根据上面初始化代码: drawSocialImpact("18-24"); 
    if (!filterAgeGroup) filterAgeGroup = "18-24"; 

    // 数据检查
    if (!socialData || socialData.length === 0) {
        console.warn("Social data is empty");
        return;
    }

    let containerWidth = container.node().getBoundingClientRect().width;
    let containerHeight = container.node().getBoundingClientRect().height;

    if (!containerWidth) containerWidth = container.node().clientWidth || 800;
    if (!containerHeight) containerHeight = container.node().clientHeight || 500;

    const margin = {top: 30, right: 30, bottom: 60, left: 30};
    const width = Math.max(0, containerWidth - margin.left - margin.right);
    const height = Math.max(0, containerHeight - margin.top - margin.bottom);

    const svg = container.append("svg")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // Definition of dimensions and plotting logic...
    const dimensions = ["dailyHours", "lateNightUsage", "addiction", "sleepQuality"];
    
    const dimensionLabels = {
        "dailyHours": "日均时长",
        "lateNightUsage": "深夜使用率(%)",
        "addiction": "成瘾指数",
        "sleepQuality": "睡眠质量"
    };

    const y = {};
    dimensions.forEach(name => {
        y[name] = d3.scaleLinear()
            .domain(d3.extent(socialData, d => +d[name]))
            .range([height, 0]);
    });

    const x = d3.scalePoint()
        .range([0, width])
        .padding(0.1)
        .domain(dimensions);

    const colorScale = d3.scaleOrdinal()
        .domain(["18-24", "25-34", "35-44", "45+"])
        .range([COLORS.danger, COLORS.tertiary, COLORS.secondary, COLORS.success]);

    function path(d) {
        return d3.line()(dimensions.map(p => [x(p), y[p](d[p])]));
    }

    const paths = svg.selectAll("myPath")
        .data(socialData)
        .join("path")
        .attr("d", path)
        .style("fill", "none")
        .style("stroke", d => colorScale(d.ageGroup))
        .style("opacity", 0) // 初始不可见
        .style("stroke-width", d => {
            if (filterAgeGroup && filterAgeGroup !== "all") {
                return d.ageGroup === filterAgeGroup ? 3 : 1;
            }
            return 2;
        });

    // 添加绘制动画
    paths.transition()
        .duration(1000)
        .delay((d, i) => i * 5) // 错开每一个数据
        .style("opacity", d => {
             // 恢复目标透明度
            if (filterAgeGroup && filterAgeGroup !== "all") {
                return d.ageGroup === filterAgeGroup ? 0.8 : 0.05;
            }
            return 0.5;
        })
        .attrTween("stroke-dasharray", function() {
            const length = this.getTotalLength();
            return d3.interpolate(`0,${length}`, `${length},${length}`);
        });

    // 绑定交互事件
    paths.on("mouseover", function(event, d) {
            d3.select(this)
                .style("stroke-width", 5)
                .style("opacity", 1)
                .style("filter", "drop-shadow(0 0 5px " + colorScale(d.ageGroup) + ")");
            
            // Mouseover behavior respects filter
            if (!filterAgeGroup || filterAgeGroup === "all") {
                svg.selectAll("path").filter(function() {
                    return this !== event.currentTarget;
                }).style("opacity", 0.05);
            }

            // 联动右图：高亮对应平台
            highlightAddictionPlatform(d.platform, true);

            showTooltip(event, `
                <div class="tooltip-title">${d.platform} (${d.ageGroup})</div>
                <div class="tooltip-row"><span>日均时长:</span><span>${d.dailyHours}h</span></div>
                <div class="tooltip-row"><span>深夜使用:</span><span>${d.lateNightUsage}%</span></div>
                <div class="tooltip-row"><span>成瘾指数:</span><span>${d.addiction}</span></div>
                <div class="tooltip-row"><span>睡眠质量:</span><span>${d.sleepQuality}</span></div>
            `);
        })
        .on("mouseout", function() {
            paths
                .style("opacity", d => {
                    if (filterAgeGroup && filterAgeGroup !== "all") {
                        return d.ageGroup === filterAgeGroup ? 0.8 : 0.05;
                    }
                    return 0.5;
                })
                .style("stroke-width", d => {
                    if (filterAgeGroup && filterAgeGroup !== "all") {
                        return d.ageGroup === filterAgeGroup ? 3 : 1;
                    }
                    return 2;
                })
                .style("filter", "none");
            
            // 取消右图高亮
            highlightAddictionPlatform(null, false);
            
            hideTooltip();
        });

    svg.selectAll("myAxis")
        .data(dimensions)
        .enter()
        .append("g")
        .attr("transform", d => `translate(${x(d)})`)
        .each(function(d) { d3.select(this).call(d3.axisLeft(y[d])); })
        .attr("class", "axis")
        .style("color", "#64748b")
        .append("text")
        .style("text-anchor", "middle")
        .attr("y", -9)
        .text(d => dimensionLabels[d])
        .style("fill", COLORS.text)
        .style("font-size", "11px")
        .style("font-weight", "bold");
        
    // 图例 (Color key)
    const legend = svg.append("g")
        .attr("transform", `translate(${width/2 - 100}, ${height + 30})`);
    
    ["18-24", "25-34", "35-44", "45+"].forEach((age, i) => {
        const g = legend.append("g").attr("transform", `translate(${i * 60}, 0)`);
        g.append("rect")
            .attr("width", 8)
            .attr("height", 8)
            .attr("rx", 2)
            .style("fill", colorScale(age));
        g.append("text")
            .attr("x", 12)
            .attr("y", 8)
            .text(age)
            .style("fill", "#94a3b8")
            .style("font-size", "10px");
    });
}

// 高亮成瘾指数图中的特定平台
function highlightAddictionPlatform(platform, highlight) {
    if (highlight && platform) {
        // 高亮指定平台
        d3.selectAll(".addiction-ring")
            .style("opacity", function() {
                return d3.select(this).attr("data-platform") === platform ? 1 : 0.2;
            })
            .style("filter", function() {
                return d3.select(this).attr("data-platform") === platform ? "drop-shadow(0 0 8px currentColor)" : "none";
            });
        
        d3.selectAll(".addiction-label")
            .style("opacity", function() {
                return d3.select(this).attr("data-platform") === platform ? 1 : 0.3;
            })
            .style("font-weight", function() {
                return d3.select(this).attr("data-platform") === platform ? "bold" : "normal";
            });
    } else {
        // 恢复所有平台
        d3.selectAll(".addiction-ring")
            .style("opacity", 1)
            .style("filter", "none");
        
        d3.selectAll(".addiction-label")
            .style("opacity", 1)
            .style("font-weight", "bold");
    }
}

// 平台成瘾指数对比 - 径向条形图 (Radial Bar Chart / Activity Rings)
function drawAddiction() {
    const container = d3.select("#addiction-chart");
    container.selectAll("*").remove();

    // 按平台计算平均成瘾指数
    const platforms = Array.from(new Set(socialData.map(d => d.platform)));
    const addictionData = platforms.map(platform => ({
        platform,
        addiction: d3.mean(socialData.filter(d => d.platform === platform), d => d.addiction)
    })).sort((a, b) => b.addiction - a.addiction); // 降序排列

    const containerWidth = container.node().getBoundingClientRect().width;
    const containerHeight = container.node().getBoundingClientRect().height;
    const width = containerWidth;
    const height = containerHeight;
    const radius = Math.min(width, height) / 2;

    const svg = container.append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(${width / 2},${height / 2})`);

    // 环形参数
    const numRings = addictionData.length;
    const ringWidth = 12;
    const gap = 8;
    const innerRadius = 30;
    
    // 角度比例尺 (0-5分 映射到 0-270度，留出缺口放图例或文字)
    const maxScore = 5; // 假设满分是5
    const angleScale = d3.scaleLinear()
        .domain([0, maxScore]) 
        .range([0, 1.5 * Math.PI]); // 270度

    const colorScale = d3.scaleOrdinal()
        .domain(platforms)
        .range(d3.schemeTableau10);

    // 绘制环形
    addictionData.forEach((d, i) => {
        // 外圈是最大值，内圈是最小值，或者反过来
        // 这里让最大值在最外圈，视觉上更明显
        const r = innerRadius + (numRings - 1 - i) * (ringWidth + gap);
        
        // 背景环
        const bgArc = d3.arc()
            .innerRadius(r)
            .outerRadius(r + ringWidth)
            .startAngle(0)
            .endAngle(1.5 * Math.PI)
            .cornerRadius(ringWidth / 2);
            
        svg.append("path")
            .attr("d", bgArc)
            .style("fill", "#333")
            .style("opacity", 0)
            .transition()
            .duration(800)
            .delay(i * 100)
            .style("opacity", 0.3);
            
        // 数值环
        const valArc = d3.arc()
            .innerRadius(r)
            .outerRadius(r + ringWidth)
            .startAngle(0)
            .endAngle(angleScale(d.addiction))
            .cornerRadius(ringWidth / 2);
            
        svg.append("path")
            // .attr("d", valArc) // 不能直接设置最终形态
            .datum({ endAngle: 0 }) // 初始状态：角度为0
            .attr("class", "addiction-ring")
            .attr("data-platform", d.platform)
            .style("fill", colorScale(d.platform))
            .attr("d", d3.arc() // 初始空路径
                .innerRadius(r)
                .outerRadius(r + ringWidth)
                .startAngle(0)
                .endAngle(0)
                .cornerRadius(ringWidth / 2)
             )
            .transition()
            .duration(1500)
            .delay(i * 100 + 200)
            .ease(d3.easeCubicOut)
            .attrTween("d", function() {
                const i = d3.interpolate(0, angleScale(d.addiction));
                return function(t) {
                    d.endAngle = i(t);
                    return d3.arc()
                        .innerRadius(r)
                        .outerRadius(r + ringWidth)
                        .startAngle(0)
                        .endAngle(i(t))
                        .cornerRadius(ringWidth / 2)();
                };
            })
            // 动画完成后绑定事件。或者直接在前边Selection上绑定。
            // 事件绑定在transition之后通常需要end事件
            .on("end", function() {
                d3.select(this)
                 .on("mouseover", (event) => {
                     showTooltip(event, `
                        <div class="tooltip-title">${d.platform}</div>
                        <div class="tooltip-row">
                            <span>成瘾指数:</span>
                            <span>${d.addiction.toFixed(1)}/5</span>
                        </div>
                    `);
                     d3.select(event.currentTarget).style("opacity", 0.8);
                })
                .on("mouseout", (event) => {
                    hideTooltip();
                    d3.select(event.currentTarget).style("opacity", 1);
                });
            });

        // 在环的起点添加图标或文字
        // 延迟显示
        svg.append("text")
            .attr("class", "addiction-label")
            .attr("data-platform", d.platform)
            .attr("x", -10) 
            .attr("y", -r - ringWidth/2 + 4) // 垂直对齐到环中心
            .attr("text-anchor", "end")
            .text(d.platform)
            .style("fill", COLORS.text)
            .style("font-size", "10px")
            .style("font-weight", "bold")
            .style("opacity", 0)
            .transition().duration(800).delay(i * 100).style("opacity", 1);
            
        // 在环的终点添加数值
        const endAngle = angleScale(d.addiction);
        // ... (省略 centroid 计算，直接显示在左侧方便)
            
        svg.append("text")
            .attr("x", -10)
            .attr("y", -r - ringWidth/2 + 14) // 标签下方
            .attr("text-anchor", "end")
            .text(d.addiction.toFixed(1))
            .style("fill", colorScale(d.platform))
            .style("font-size", "9px")
            .style("opacity", 0)
            .transition().duration(800).delay(i * 100 + 500).style("opacity", 1);
    });
    
    // 中心添加标题
    svg.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", "0.35em")
        .text("成瘾指数")
        .style("fill", COLORS.text)
        .style("font-size", "12px")
        .style("font-weight", "bold");
}

// ===== 第四页：全球对比 =====
function initGlobalPage() {
    drawWorldMap();
    drawGlobalRanking();
    // drawGlobalBubble(); // 已注释，不再使用
    
    // 绑定排序按钮
    d3.select("#sortAsc").on("click", function() {
        d3.selectAll("#sortAsc, #sortDesc").classed("active", false);
        d3.select(this).classed("active", true);
        drawGlobalRanking(true);
    });
    
    d3.select("#sortDesc").on("click", function() {
        d3.selectAll("#sortAsc, #sortDesc").classed("active", false);
        d3.select(this).classed("active", true);
        drawGlobalRanking(false);
    });
}

// 全球熬夜率地图
function drawWorldMap() {
    const container = d3.select("#global-map-chart");
    if (container.empty()) return;

    container.selectAll("*").remove();

    const containerWidth = container.node().getBoundingClientRect().width;
    const containerHeight = container.node().getBoundingClientRect().height;
    const margin = { top: 6, right: 6, bottom: 6, left: 6 };
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    const svg = container.append("svg")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    const normalizeName = name => (name || "").toLowerCase().replace(/[^a-z]/g, "");
    const NAME_ALIASES = {
        "unitedstatesofamerica": "unitedstates",
        "unitedstates": "unitedstates",
        "republicofkorea": "southkorea",
        "korearepublicof": "southkorea",
        "viet nam": "vietnam"
    };

    const dataMap = new Map(globalData.map(d => [normalizeName(d.country), d]));
    const lateNightExtent = d3.extent(globalData, d => d.lateNightRate);
    const colorScale = d3.scaleLinear()
        .domain(lateNightExtent)
        .range([COLORS.success, COLORS.danger])
        .clamp(true);
    const heightScale = d3.scaleLinear()
        .domain(lateNightExtent)
        .range([1.5, 14])
        .clamp(true);

    const renderMap = (geojson) => {
        const radius = Math.min(width, height) / 2;
        const projection = d3.geoOrthographic()
            .translate([width / 2, height / 2])
            .scale(radius - 4)
            .rotate(worldRotation);

        const path = d3.geoPath(projection);
        const graticule = d3.geoGraticule();
        const sphere = { type: "Sphere" };
        const getCountryStats = (feature) => {
            const key = normalizeName(feature.properties?.name);
            const alias = NAME_ALIASES[key];
            return dataMap.get(key) || dataMap.get(alias);
        };

        const ocean = svg.append("path")
            .datum(sphere)
            .attr("fill", "#0f172a")
            .attr("stroke", COLORS.secondary)
            .attr("stroke-opacity", 0.25);

        const graticulePath = svg.append("path")
            .datum(graticule())
            .attr("fill", "none")
            .attr("stroke", "rgba(255,255,255,0.08)")
            .attr("stroke-width", 0.6);

        // 真实凸起效果：为每个国家叠加多层偏移路径，层数与熬夜率成正比
        const countryGroups = svg.append("g")
            .attr("cursor", "grab")
            .selectAll("g.country")
            .data(geojson.features)
            .join("g")
            .attr("class", "country");

        countryGroups.append("g")
            .attr("class", "extrusion-layers")
            .selectAll("path")
            .data(d => {
                const data = getCountryStats(d);
                if (!data) return [];
                const h = heightScale(data.lateNightRate);
                const layers = Math.max(2, Math.round(h));
                return d3.range(layers).map(layer => ({ feature: d, layer, h, data }));
            })
            .join("path")
            .attr("class", "extrusion-layer")
            .attr("d", d => path(d.feature))
            .attr("transform", d => `translate(${d.layer * 0.55},${-d.layer * 0.65})`)
            .attr("fill", d => {
                const base = d3.color(colorScale(d.data.lateNightRate)) || d3.color("#1f2937");
                return base.darker(0.9 + d.layer * 0.08);
            })
            .attr("opacity", 0.9)
            .attr("stroke", "none");

        const countries = countryGroups.append("path")
            .attr("class", "country-top")
            .attr("d", d => path(d))
            .attr("fill", d => {
                const data = getCountryStats(d);
                return data ? colorScale(data.lateNightRate) : "#1f2937";
            })
            .attr("stroke", "#0a0e1a")
            .attr("stroke-width", 0.7)
            .style("opacity", 1);
        
        countryGroups.selectAll(".country-top")
            .on("mouseover", (event, d) => {
                const data = getCountryStats(d);
                const hasData = Boolean(data);

                d3.select(event.currentTarget)
                    .attr("stroke", COLORS.primary)
                    .attr("stroke-width", 1.6)
                    .raise();

                showTooltip(event, `
                    <div class="tooltip-title">${d.properties?.name || "未知国家"}</div>
                    <div class="tooltip-row">
                        <span>熬夜率:</span>
                        <span>${hasData ? `${data.lateNightRate}%` : "暂无数据"}</span>
                    </div>
                    <div class="tooltip-row">
                        <span>平均睡眠:</span>
                        <span>${hasData ? `${data.avgSleep} 小时` : "暂无数据"}</span>
                    </div>
                    <div class="tooltip-row">
                        <span>周工作时长:</span>
                        <span>${hasData ? `${data.workHours} 小时` : "暂无数据"}</span>
                    </div>
                    <div class="tooltip-row">
                        <span>网络使用:</span>
                        <span>${hasData ? `${data.internetHours} 小时/天` : "暂无数据"}</span>
                    </div>
                    ${hasData ? `<div class="tooltip-row">
                        <span>压力水平:</span>
                        <span>${data.stressLevel}/10</span>
                    </div>
                    <div class="tooltip-row">
                        <span>睡眠障碍率:</span>
                        <span>${data.disorderRate}%</span>
                    </div>` : ""}
                `);
            })
            .on("mouseout", (event) => {
                hideTooltip();
                d3.select(event.currentTarget)
                    .attr("stroke", "#0a0e1a")
                    .attr("stroke-width", 0.7);
            });

        const redraw = () => {
            ocean.attr("d", path);
            graticulePath.attr("d", path);
            countryGroups.selectAll(".extrusion-layer").attr("d", d => path(d.feature));
            countries.attr("d", d => path(d));
        };

        redraw();

        const drag = d3.drag()
            .on("start", () => countries.attr("cursor", "grabbing"))
            .on("drag", (event) => {
                const sensitivity = 0.4;
                worldRotation[0] += event.dx * sensitivity;
                worldRotation[1] -= event.dy * sensitivity;
                worldRotation[1] = Math.max(-90, Math.min(90, worldRotation[1]));
                projection.rotate(worldRotation);
                redraw();
            })
            .on("end", () => countries.attr("cursor", "grab"));

        svg.call(drag);

        // 图例渲染到HTML容器
        const legendContainer = d3.select("#globe-legend");
        legendContainer.html("");
        
        const svgLegend = legendContainer.append("svg")
            .attr("width", 180)
            .attr("height", 24);
        
        const defsLegend = svgLegend.append("defs");
        const gradientLegend = defsLegend.append("linearGradient")
            .attr("id", "map-gradient-legend")
            .attr("x1", "0%")
            .attr("x2", "100%");
        
        gradientLegend.append("stop").attr("offset", "0%").attr("stop-color", COLORS.success);
        gradientLegend.append("stop").attr("offset", "100%").attr("stop-color", COLORS.danger);
        
        svgLegend.append("rect")
            .attr("x", 20)
            .attr("y", 4)
            .attr("width", 120)
            .attr("height", 10)
            .attr("fill", "url(#map-gradient-legend)")
            .attr("stroke", COLORS.primary)
            .attr("stroke-width", 1);
        
        svgLegend.append("text")
            .attr("x", 18)
            .attr("y", 20)
            .style("fill", COLORS.text)
            .style("font-size", "11px")
            .style("text-anchor", "end")
            .text("低");
        
        svgLegend.append("text")
            .attr("x", 142)
            .attr("y", 20)
            .style("fill", COLORS.text)
            .style("font-size", "11px")
            .style("text-anchor", "start")
            .text("高");
    };

    if (worldGeoData) {
        renderMap(worldGeoData);
    } else {
        d3.json("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json")
            .then(world => {
                worldGeoData = topojson.feature(world, world.objects.countries);
                renderMap(worldGeoData);
            })
            .catch(err => {
                console.error("世界地图加载失败", err);
                container.append("div")
                    .style("color", COLORS.text)
                    .style("padding", "10px")
                    .text("世界地图加载失败，请检查网络连接。");
            });
    }
}

// 全球睡眠时长排名 - 极坐标辐射柱状图 (Circular Barplot)
function drawGlobalRanking(ascending = true) {
    const container = d3.select("#global-ranking-chart");
    container.selectAll("*").remove();

    // 排序逻辑
    const allData = [...globalData].sort((a, b) => 
        ascending ? a.avgSleep - b.avgSleep : b.avgSleep - a.avgSleep
    );
    
    // 如果数据太多，取 Top 40 以保证美观，否则圆周太挤
    const sortedData = allData.length > 40 ? allData.slice(0, 40) : allData;

    const containerWidth = container.node().getBoundingClientRect().width;
    const containerHeight = container.node().getBoundingClientRect().height;
    // 增加边距以容纳标签
    const margin = {top: 20, right: 20, bottom: 20, left: 20};
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;
    
    // 半径设置
    const innerRadius = 50; 
    const outerRadius = Math.min(width, height) / 2 - 30; // 留出标签空间

    const svg = container.append("svg")
        .attr("width", containerWidth)
        .attr("height", containerHeight)
        .append("g")
        .attr("transform", `translate(${containerWidth / 2},${containerHeight / 2})`);

    // X轴：国家（角度）
    const x = d3.scaleBand()
        .range([0, 2 * Math.PI])
        .domain(sortedData.map(d => d.country))
        .align(0);

    // Y轴：睡眠时长（半径）
    // 为了拉开差距且保证视觉效果，Domain 可以从较小值开始
    const minVal = d3.min(sortedData, d => d.avgSleep);
    const maxVal = d3.max(sortedData, d => d.avgSleep);
    // 动态调整Y轴范围，让柱子长度差异更明显，但至少保留其长度的一半作为基准
    const yMin = Math.max(0, minVal - 2); 
    
    const y = d3.scaleLinear()
        .range([innerRadius, outerRadius])
        .domain([yMin, maxVal]); 

    // 颜色比例尺 - 使用 HCL 插值获得更鲜艳的过渡
    const colorScale = d3.scaleSequential()
        .domain([minVal, maxVal]) 
        .interpolator(d3.interpolateHcl(COLORS.danger, COLORS.success)); 

    // 添加同心圆参考线 (Grid)
    const yTicks = y.ticks(3);
    svg.append("g")
        .selectAll("circle")
        .data(yTicks)
        .join("circle")
        .attr("fill", "none")
        .attr("stroke", "rgba(255,255,255,0.05)")
        .attr("stroke-dasharray", "3,3")
        .attr("r", y);
        
    // 刻度文字
    svg.append("g")
        .selectAll("text")
        .data(yTicks)
        .join("text")
        .attr("y", d => -y(d))
        .attr("dy", "0.35em")
        .attr("fill", "rgba(255,255,255,0.2)")
        .attr("font-size", "8px")
        .attr("text-anchor", "middle")
        .style("pointer-events", "none") // 避免干扰交互
        .text(d => d + "h");

    // 初始状态用Arc (半径为 0 或 innerRadius)
    const arcZero = d3.arc()
        .innerRadius(innerRadius)
        .outerRadius(innerRadius) // 半径从内部开始
        .startAngle(d => x(d.country))
        .endAngle(d => x(d.country) + x.bandwidth())
        .padAngle(0.02)
        .padRadius(innerRadius);

    // 绘制辐射柱状图
    const arc = d3.arc()
        .innerRadius(innerRadius)
        .outerRadius(d => y(d.avgSleep))
        .startAngle(d => x(d.country))
        .endAngle(d => x(d.country) + x.bandwidth())
        .padAngle(0.02)
        .padRadius(innerRadius);

    // 高亮时的 Arc 生成器
    const arcHover = d3.arc()
        .innerRadius(innerRadius)
        .outerRadius(d => y(d.avgSleep) + 8) // 变长
        .startAngle(d => x(d.country) - 0.01) // 变宽
        .endAngle(d => x(d.country) + x.bandwidth() + 0.01)
        .padAngle(0.02)
        .padRadius(innerRadius);

    svg.append("g")
        .selectAll("path")
        .data(sortedData)
        .join("path")
        .attr("fill", d => colorScale(d.avgSleep))
        .attr("d", arcZero) // 初始：长度为0
        .attr("cursor", "pointer")
        .attr("stroke", "none")
        .transition() // 生长动画
        .duration(1000)
        .delay((d, i) => i * 20)
        .ease(d3.easeCubicOut)
        .attr("d", arc);

    // 绑定事件 (Transition后需重新选择)
    svg.selectAll("path")
        .on("mouseover", function(event, d) {
            // 高亮效果
            d3.select(this)
                .transition().duration(200)
                .attr("d", arcHover)
                .attr("filter", "drop-shadow(0 0 5px " + colorScale(d.avgSleep) + ")");
            
            // 更新中心文字
            updateCenterText(d);
            
            // 简单的 Tooltip 辅助
            showTooltip(event, `
                <div class="tooltip-title">${d.country}</div>
                <div class="tooltip-row">
                    <span>平均睡眠:</span>
                    <span>${d.avgSleep}小时</span>
                </div>
                 <div class="tooltip-row">
                    <span>排名:</span>
                    <span>#${sortedData.indexOf(d) + 1}</span>
                </div>
                <div class="tooltip-row">
                    <span>熬夜率:</span>
                    <span>${d.lateNightRate}%</span>
                </div>
            `);
        })
        .on("mouseout", function(event, d) {
            d3.select(this)
                .transition().duration(200)
                .attr("d", arc)
                .attr("filter", "none");
                
            hideTooltip();
            resetCenterText();
        });

    // 标签
    const labelGroup = svg.append("g")
        .selectAll("g")
        .data(sortedData)
        .join("g")
        .attr("text-anchor", function(d) { return (x(d.country) + x.bandwidth() / 2 + Math.PI) % (2 * Math.PI) < Math.PI ? "end" : "start"; })
        .attr("transform", function(d) { return "rotate(" + ((x(d.country) + x.bandwidth() / 2) * 180 / Math.PI - 90) + ")" + "translate(" + (y(d.avgSleep) + 5) + ",0)"; })
        .style("opacity", 0); // 初始隐藏
    
    // 标签入场动画
    labelGroup.transition()
        .duration(1000)
        .delay((d,i) => 800 + i * 20)
        .style("opacity", 1);

    labelGroup.append("text")
        .text(d => d.country)
        .attr("transform", function(d) { return (x(d.country) + x.bandwidth() / 2 + Math.PI) % (2 * Math.PI) < Math.PI ? "rotate(180)" : "rotate(0)"; })
        .style("font-size", "9px")
        .style("fill", "rgba(255,255,255,0.6)")
        .attr("alignment-baseline", "middle");

    // 中心文本区域
    const centerGroup = svg.append("g")
        .attr("class", "center-text")
        .style("pointer-events", "none");
    
    function resetCenterText() {
        centerGroup.html("");
        centerGroup.append("text")
            .attr("y", -8)
            .attr("text-anchor", "middle")
            .style("font-size", "10px")
            .style("fill", COLORS.text)
            .style("opacity", 0.6)
            .text("全球平均");
            
        centerGroup.append("text")
            .attr("y", 12)
            .attr("text-anchor", "middle")
            .style("font-size", "18px")
            .style("font-family", "Orbitron")
            .style("fill", COLORS.primary)
            .text(d3.mean(sortedData, d => d.avgSleep).toFixed(1) + "h");
    }
    
    function updateCenterText(d) {
        centerGroup.html("");
        // 自适应字体大小
        let name = d.country;
        let fontSize = "11px";
        if (name.length > 12) fontSize = "9px";
        
        centerGroup.append("text")
            .attr("y", -8)
            .attr("text-anchor", "middle")
            .style("font-size", fontSize)
            .style("fill", COLORS.text)
            .style("font-weight", "bold")
            .text(name);
            
        centerGroup.append("text")
            .attr("y", 12)
            .attr("text-anchor", "middle")
            .style("font-size", "18px")
            .style("font-family", "Orbitron")
            .style("fill", colorScale(d.avgSleep))
            .text(d.avgSleep + "h");
    }

    resetCenterText();

    // 渐变图例（睡眠时长）- 渲染到HTML容器 (保持原样，仅更新文字描述以匹配新图表风格)
    const legendContainer = d3.select("#ranking-legend");
    legendContainer.html("");
    
    const svgLegend = legendContainer.append("svg")
        .attr("width", 160)
        .attr("height", 24);
    
    const defsLegend = svgLegend.append("defs");
    const gradientLegend = defsLegend.append("linearGradient")
        .attr("id", "ranking-gradient-legend")
        .attr("x1", "0%")
        .attr("x2", "100%");
    
    gradientLegend.append("stop").attr("offset", "0%").attr("stop-color", COLORS.danger);
    gradientLegend.append("stop").attr("offset", "100%").attr("stop-color", COLORS.success);
    
    svgLegend.append("rect")
        .attr("x", 20)
        .attr("y", 4)
        .attr("width", 100)
        .attr("height", 10)
        .attr("fill", "url(#ranking-gradient-legend)")
        .attr("stroke", "rgba(255,255,255,0.2)")
        .attr("stroke-width", 1)
        .attr("rx", 2);
    
    svgLegend.append("text")
        .attr("x", 18)
        .attr("y", 20)
        .style("fill", COLORS.text)
        .style("font-size", "10px")
        .style("text-anchor", "end")
        .text("短");
    
    svgLegend.append("text")
        .attr("x", 122)
        .attr("y", 20)
        .style("fill", COLORS.text)
        .style("font-size", "10px")
        .style("text-anchor", "start")
        .text("长");
}
