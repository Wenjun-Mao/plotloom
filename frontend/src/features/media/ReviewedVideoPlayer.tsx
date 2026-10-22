import { useRef, useState, type CSSProperties } from "react";
import { Button } from "../../components";

type PlayerProps = {
  src: string;
  testId: string;
  kind: "原片" | "播放片段";
  style?: CSSProperties;
};

function SourcePlayer({ src, testId, kind, style }: PlayerProps) {
  const player = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<{ code: number; message: string } | null>(null);
  return <div className="reviewed-video-player">
    <video ref={player} controls preload="metadata" src={src} style={style}
      aria-label={`${kind}预览`} data-testid={testId} data-reviewed-media-preview
      onError={(event) => {
        const failure = event.currentTarget.error;
        setError({ code: failure?.code ?? 0, message: failure?.message ?? "" });
      }}
      onLoadedData={() => setError(null)}
      onPlay={(event) => {
        document.querySelectorAll<HTMLVideoElement>("video[data-reviewed-media-preview]")
          .forEach(video => { if (video !== event.currentTarget) video.pause(); });
      }} />
    {error && <div role="alert" className="notice warning reviewed-video-error">
      <strong>浏览器未能播放这份{kind}。</strong>
      <small>原片、片段和审阅记录仍保留。重新加载仅尝试重新打开当前视频，不会重新生成、改变选用结果或自动播放。</small>
      <Button onClick={() => { setError(null); player.current?.load(); }}>重新加载{kind}</Button>
      <details><summary>播放错误详情</summary>
        <small>媒体错误代码：{error.code}</small>
        {error.message && <pre>{error.message}</pre>}
      </details>
    </div>}
  </div>;
}

/** A changed media identity owns a fresh error/retry state, never a prior preview's. */
export function ReviewedVideoPlayer(props: PlayerProps) {
  return <SourcePlayer key={props.src} {...props} />;
}
