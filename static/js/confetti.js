/* Tiny confetti burst — no library, ~1KB */
(function () {
    const COLORS = ['#1e40af', '#16a34a', '#f59e0b', '#dc2626', '#7c3aed', '#06b6d4'];

    window.burstConfetti = function (count = 40) {
        const container = document.createElement('div');
        container.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;';
        document.body.appendChild(container);

        for (let i = 0; i < count; i++) {
            const piece = document.createElement('div');
            const size = 6 + Math.random() * 6;
            piece.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                background: ${COLORS[Math.floor(Math.random() * COLORS.length)]};
                left: ${50 + (Math.random() - 0.5) * 20}%;
                top: 40%;
                border-radius: ${Math.random() > 0.5 ? '50%' : '0'};
                transform: rotate(${Math.random() * 360}deg);
                will-change: transform, opacity;
            `;
            container.appendChild(piece);

            const angle = (Math.random() - 0.5) * Math.PI;
            const velocity = 200 + Math.random() * 300;
            const vx = Math.sin(angle) * velocity;
            const vy = -Math.abs(Math.cos(angle)) * velocity;

            const start = performance.now();
            const duration = 1800 + Math.random() * 800;

            function animate(now) {
                const t = (now - start) / duration;
                if (t >= 1) { piece.remove(); return; }
                const x = vx * t;
                const y = vy * t + 0.5 * 500 * t * t;   // gravity
                piece.style.transform = `translate(${x}px, ${y}px) rotate(${t * 720}deg)`;
                piece.style.opacity = 1 - t;
                requestAnimationFrame(animate);
            }
            requestAnimationFrame(animate);
        }

        setTimeout(() => container.remove(), 3000);
    };
})();