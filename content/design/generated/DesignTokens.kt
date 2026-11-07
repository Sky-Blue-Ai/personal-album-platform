// 自动生成，勿手改。源文件 content/design/tokens.json，生成器 tools/build_design_tokens.py
package design

/**
 * 设计令牌。纯 Kotlin 常量，不依赖 androidx.compose，可在 shared / 服务端直接引用。
 * Compose 侧映射：
 *   Color(DesignTokens.color.surface)            // Long → Color
 *   DesignTokens.type.bodyMd.size.sp             // Float → TextUnit
 *   FontFamily(Font(...))                        // 字体文件见 docs/design-system.md
 */
object DesignTokens {
    object color {
        const val surface: Long = 0xFFF9F9F9
        const val surface_lowest: Long = 0xFFFFFFFF
        const val surface_low: Long = 0xFFF3F3F3
        const val surface_container: Long = 0xFFEEEEEE
        const val surface_high: Long = 0xFFE8E8E8
        const val surface_highest: Long = 0xFFE2E2E2
        const val surface_dim: Long = 0xFFDADADA
        const val on_surface: Long = 0xFF1A1C1C
        const val on_surface_variant: Long = 0xFF444748
        const val on_surface_muted: Long = 0xFF5F5E5E
        const val on_surface_disabled: Long = 0xFF858383
        const val outline: Long = 0xFF747878
        const val outline_variant: Long = 0xFFC4C7C7
        const val inverse_surface: Long = 0xFF2F3131
        const val inverse_on_surface: Long = 0xFFF0F1F1
        const val accent: Long = 0xFF9C3327
        const val accent_on: Long = 0xFFFFFFFF
        const val accent_soft: Long = 0xFFF4E7E4
        const val license_cc0: Long = 0xFF2F6B4F
        const val license_pending: Long = 0xFF8A6A1F
        const val license_restricted: Long = 0xFF7A1F16
        const val license_on: Long = 0xFFFFFFFF
        const val error: Long = 0xFFBA1A1A
        const val error_container: Long = 0xFFFFDAD6
        const val error_on_container: Long = 0xFF93000A
    }

    object space {
        const val space_3xs: Float = 4.0f  // 0.25rem
        const val space_2xs: Float = 8.0f  // 0.5rem
        const val xs: Float = 12.0f  // 0.75rem
        const val sm: Float = 16.0f  // 1rem
        const val md: Float = 24.0f  // 1.5rem
        const val lg: Float = 32.0f  // 2rem
        const val xl: Float = 48.0f  // 3rem
        const val space_2xl: Float = 64.0f  // 4rem
        const val space_3xl: Float = 96.0f  // 6rem
        const val space_4xl: Float = 128.0f  // 8rem
    }

    object radius {
        const val sm: Float = 4.0f  // 0.25rem
        const val md: Float = 8.0f  // 0.5rem
        const val lg: Float = 12.0f  // 0.75rem
        const val full: Float = 9999.0f  // 9999px
    }

    object type {
        object displayXl {
            const val sizePx: Float = 72.0f
            const val lineHeightMultiplier: Float = 1.02f
            const val letterSpacingEm: Float = -0.02f
            const val weight: Int = 400
            const val family: String = "display"
        }
        object displayLg {
            const val sizePx: Float = 56.0f
            const val lineHeightMultiplier: Float = 1.06f
            const val letterSpacingEm: Float = -0.015f
            const val weight: Int = 400
            const val family: String = "display"
        }
        object displayMd {
            const val sizePx: Float = 44.0f
            const val lineHeightMultiplier: Float = 1.1f
            const val letterSpacingEm: Float = -0.01f
            const val weight: Int = 400
            const val family: String = "display"
        }
        object headlineLg {
            const val sizePx: Float = 32.0f
            const val lineHeightMultiplier: Float = 1.25f
            const val letterSpacingEm: Float = 0.0f
            const val weight: Int = 500
            const val family: String = "serif"
        }
        object headlineMd {
            const val sizePx: Float = 24.0f
            const val lineHeightMultiplier: Float = 1.35f
            const val letterSpacingEm: Float = 0.0f
            const val weight: Int = 500
            const val family: String = "serif"
        }
        object headlineSm {
            const val sizePx: Float = 20.0f
            const val lineHeightMultiplier: Float = 1.4f
            const val letterSpacingEm: Float = 0.0f
            const val weight: Int = 500
            const val family: String = "serif"
        }
        object bodyLg {
            const val sizePx: Float = 17.0f
            const val lineHeightMultiplier: Float = 1.75f
            const val letterSpacingEm: Float = 0.0f
            const val weight: Int = 400
            const val family: String = "sans"
        }
        object bodyMd {
            const val sizePx: Float = 15.0f
            const val lineHeightMultiplier: Float = 1.7f
            const val letterSpacingEm: Float = 0.0f
            const val weight: Int = 400
            const val family: String = "sans"
        }
        object bodySm {
            const val sizePx: Float = 13.0f
            const val lineHeightMultiplier: Float = 1.6f
            const val letterSpacingEm: Float = 0.0f
            const val weight: Int = 400
            const val family: String = "sans"
        }
        object labelLg {
            const val sizePx: Float = 12.0f
            const val lineHeightMultiplier: Float = 1.4f
            const val letterSpacingEm: Float = 0.12f
            const val weight: Int = 500
            const val family: String = "sans"
        }
        object labelSm {
            const val sizePx: Float = 11.0f
            const val lineHeightMultiplier: Float = 1.4f
            const val letterSpacingEm: Float = 0.16f
            const val weight: Int = 500
            const val family: String = "sans"
        }
    }

    object font {
        const val display: String = "Bodoni Moda | Noto Serif SC | Source Han Serif SC | Songti SC | STSong | serif"
        const val serif: String = "Noto Serif SC | Source Han Serif SC | Songti SC | STSong | Georgia | serif"
        const val sans: String = "Inter | Noto Sans SC | Source Han Sans SC | PingFang SC | Microsoft YaHei | system-ui | sans-serif"
        const val mono: String = "JetBrains Mono | SF Mono | ui-monospace | Menlo | monospace"
    }
}
