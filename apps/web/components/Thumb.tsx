"use client";

/** 机构 CDN 的缩略图可能被墙/失效，降级成文字占位而不是空白框 */
export default function Thumb({ src, alt }: { src: string; alt: string }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={(e) => {
        const img = e.currentTarget;
        img.style.display = "none";
        img.parentElement?.setAttribute("data-nophoto", "1");
      }}
    />
  );
}
