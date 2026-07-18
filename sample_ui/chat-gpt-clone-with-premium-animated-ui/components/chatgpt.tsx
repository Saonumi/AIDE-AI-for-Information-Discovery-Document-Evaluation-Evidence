"use client"

import { DropdownMenuTrigger } from "@/components/ui/dropdown-menu"

import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip"
import * as React from "react"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
} from "@/components/ui/dropdown-menu"
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
  InputGroupTextarea,
} from "@/components/ui/input-group"
import { Item, ItemContent, ItemDescription, ItemTitle } from "@/components/ui/item"
import { Kbd } from "@/components/ui/kbd"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  PlusSignIcon,
  AttachmentIcon,
  SparklesIcon,
  ShoppingBag01Icon,
  MagicWand05Icon,
  Cursor01Icon,
  MoreHorizontalCircle01Icon,
  Share03Icon,
  BookIcon,
  GlobalIcon,
  PenIcon,
  AudioWave01Icon,
  ArrowUp02Icon,
  ArrowDown01Icon,
  Settings01Icon,
  FolderIcon,
  CheckmarkCircle02Icon,
  BulbIcon,
  Moon02Icon,
  Sun03Icon,
} from "@hugeicons/core-free-icons"
import { useTheme } from "@/components/theme-provider"

const categories = [
  {
    id: "homework",
    label: "Homework",
  },
  {
    id: "writing",
    label: "Writing",
  },
  {
    id: "health",
    label: "Health",
  },
  {
    id: "travel",
    label: "Travel",
  },
]

export function ChatGPT() {
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(true)
  const [animationsEnabled, setAnimationsEnabled] = React.useState(true)

  React.useEffect(() => {
    const stored = localStorage.getItem("animations-enabled")
    if (stored !== null) {
      setAnimationsEnabled(stored === "true")
    }
  }, [])

  const toggleAnimations = () => {
    const newValue = !animationsEnabled
    setAnimationsEnabled(newValue)
    localStorage.setItem("animations-enabled", String(newValue))
  }

  return (
    <TooltipProvider>
      <div className="flex h-screen w-full overflow-hidden bg-background">
        {/* Sidebar */}
        <div
          className={`flex flex-col bg-muted/30 transition-all duration-300 relative ${isSidebarOpen ? "w-64" : "w-0"}`}
        >
          {animationsEnabled && (
            <div className="pointer-events-none absolute right-0 top-0 h-full w-[1px] bg-gradient-to-b from-transparent via-orange-500 to-transparent animate-border-1 opacity-50" />
          )}
          {isSidebarOpen && (
            <div className="flex h-full flex-col">
              {/* Sidebar Header */}
              <div className="flex items-center justify-between p-4 relative">
                {animationsEnabled && (
                  <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-400 to-transparent animate-border-2 opacity-40" />
                )}
                <Button variant="ghost" size="icon-sm" onClick={() => setIsSidebarOpen(false)}>
                  <HugeiconsIcon icon={ArrowDown01Icon} strokeWidth={2} className="rotate-90" />
                </Button>
                <CreateProjectDialog />
              </div>

              {/* Chat History */}
              <div className="flex-1 overflow-y-auto p-2">
                <div className="space-y-1">
                  <Button variant="ghost" className="w-full justify-start gap-2 text-sm">
                    <HugeiconsIcon icon={SparklesIcon} strokeWidth={2} className="size-4" />
                    Copenhagen Trip Planning
                  </Button>
                  <Button variant="ghost" className="w-full justify-start gap-2 text-sm">
                    <HugeiconsIcon icon={BookIcon} strokeWidth={2} className="size-4" />
                    Study Session
                  </Button>
                  <Button variant="ghost" className="w-full justify-start gap-2 text-sm">
                    <HugeiconsIcon icon={PenIcon} strokeWidth={2} className="size-4" />
                    Writing Project
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Main Chat Area */}
        <div className="flex flex-1 flex-col">
          {/* Chat Header */}
          <div className="flex items-center justify-between p-4 relative">
            {animationsEnabled && (
              <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-500 to-transparent animate-border-3 opacity-60" />
            )}
            {!isSidebarOpen && (
              <Button variant="ghost" size="icon-sm" onClick={() => setIsSidebarOpen(true)}>
                <HugeiconsIcon icon={ArrowDown01Icon} strokeWidth={2} className="-rotate-90" />
              </Button>
            )}
            <div className="absolute left-1/2 -translate-x-1/2">
              <img src="/images/v0-logo.png" alt="v0" className="h-8 w-8 object-contain" />
            </div>
            <ModelSelector />
            <div className="ml-auto flex items-center gap-1">
              <AnimationToggle enabled={animationsEnabled} onToggle={toggleAnimations} />
              <ThemeToggle />
              <Button variant="ghost" size="icon-sm">
                <HugeiconsIcon icon={MoreHorizontalCircle01Icon} strokeWidth={2} />
              </Button>
            </div>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="mx-auto max-w-3xl space-y-6">
              {/* Welcome State */}
              <div className="relative flex flex-1 items-center justify-center text-center">
                <div className="relative z-10">
                  <h2 className="mb-2 text-2xl font-semibold">How can I help you today?</h2>
                  <p className="text-muted-foreground text-sm">Ask me anything or choose from the suggestions below</p>
                </div>
              </div>
            </div>
          </div>

          {/* Prompt Form at Bottom */}
          <div className="p-4 relative">
            {animationsEnabled && (
              <div className="pointer-events-none absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-orange-500/80 to-transparent animate-border-1 opacity-50" />
            )}
            <div className="mx-auto max-w-3xl">
              <PromptForm animationsEnabled={animationsEnabled} />
            </div>
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}

export { ChatGPT as ChatGPTBlock }

function PromptForm({ animationsEnabled }: { animationsEnabled: boolean }) {
  const [dictateEnabled, setDictateEnabled] = React.useState(false)

  return (
    <div className="space-y-2">
      <Field>
        <FieldLabel htmlFor="prompt" className="sr-only">
          Prompt
        </FieldLabel>
        <div className="relative">
          {animationsEnabled && (
            <div className="pointer-events-none absolute -inset-[2px] rounded-lg bg-gradient-to-r from-transparent via-orange-500 to-transparent animate-border-glow opacity-75" />
          )}
          <InputGroup className="relative bg-background">
            <InputGroupTextarea id="prompt" placeholder="Ask anything" />
            <InputGroupAddon align="block-end">
              <DropdownMenu>
                <Tooltip>
                  <DropdownMenuTrigger asChild>
                    <TooltipTrigger asChild>
                      <InputGroupButton
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => setDictateEnabled(!dictateEnabled)}
                        className="rounded-4xl"
                      >
                        <HugeiconsIcon icon={PlusSignIcon} strokeWidth={2} />
                      </InputGroupButton>
                    </TooltipTrigger>
                  </DropdownMenuTrigger>
                  <TooltipContent>
                    Add files and more <Kbd>/</Kbd>
                  </TooltipContent>
                </Tooltip>
                <DropdownMenuContent className="w-56" onCloseAutoFocus={(e) => e.preventDefault()}>
                  <DropdownMenuItem>
                    <HugeiconsIcon icon={AttachmentIcon} strokeWidth={2} />
                    Add photos & files
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <HugeiconsIcon icon={SparklesIcon} strokeWidth={2} />
                    Deep research
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <HugeiconsIcon icon={ShoppingBag01Icon} strokeWidth={2} />
                    Shopping research
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <HugeiconsIcon icon={MagicWand05Icon} strokeWidth={2} />
                    Create image
                  </DropdownMenuItem>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <DropdownMenuItem>
                        <HugeiconsIcon icon={Cursor01Icon} strokeWidth={2} />
                        Agent mode
                      </DropdownMenuItem>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <div className="font-medium">35 left</div>
                      <div className="text-primary-foreground/80 text-xs">More available for purchase</div>
                    </TooltipContent>
                  </Tooltip>
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <HugeiconsIcon icon={MoreHorizontalCircle01Icon} strokeWidth={2} />
                      More
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent>
                      <DropdownMenuItem>
                        <HugeiconsIcon icon={Share03Icon} strokeWidth={2} />
                        Add sources
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                        <HugeiconsIcon icon={BookIcon} strokeWidth={2} />
                        Study and learn
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                        <HugeiconsIcon icon={GlobalIcon} strokeWidth={2} />
                        Web search
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                        <HugeiconsIcon icon={PenIcon} strokeWidth={2} />
                        Canvas
                      </DropdownMenuItem>
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                </DropdownMenuContent>
              </DropdownMenu>
              <Tooltip>
                <TooltipTrigger asChild>
                  <InputGroupButton
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setDictateEnabled(!dictateEnabled)}
                    className="ml-auto rounded-4xl"
                  >
                    <HugeiconsIcon icon={AudioWave01Icon} strokeWidth={2} />
                  </InputGroupButton>
                </TooltipTrigger>
                <TooltipContent>Dictate</TooltipContent>
              </Tooltip>
              <InputGroupButton size="icon-sm" variant="default" className="rounded-4xl">
                <HugeiconsIcon icon={ArrowUp02Icon} strokeWidth={2} />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </div>
      </Field>
    </div>
  )
}

function ModelSelector() {
  const [chatMode, setChatMode] = React.useState("auto")
  const [chatModel, setChatModel] = React.useState("gpt-5.1")

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="gap-2">
          ChatGPT 5.1
          <HugeiconsIcon icon={ArrowDown01Icon} strokeWidth={2} className="text-muted-foreground size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-60" align="start">
        <DropdownMenuLabel className="text-muted-foreground text-xs font-normal">GPT-5.1</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={chatMode} onValueChange={setChatMode}>
          <DropdownMenuRadioItem value="auto">
            <Item size="xs" className="p-0">
              <ItemContent>
                <ItemTitle>Auto</ItemTitle>
                <ItemDescription className="text-xs">Decides how long to think</ItemDescription>
              </ItemContent>
            </Item>
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="instant">
            <Item size="xs" className="p-0">
              <ItemContent>
                <ItemTitle>Instant</ItemTitle>
                <ItemDescription className="text-xs">Answers right away</ItemDescription>
              </ItemContent>
            </Item>
          </DropdownMenuRadioItem>
          <DropdownMenuRadioItem value="thinking">
            <Item size="xs" className="p-0">
              <ItemContent>
                <ItemTitle>Thinking</ItemTitle>
                <ItemDescription className="text-xs">Thinks longer for better answers</ItemDescription>
              </ItemContent>
            </Item>
          </DropdownMenuRadioItem>
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />
        <DropdownMenuSub>
          <DropdownMenuSubTrigger>
            <span className="font-medium">Legacy models</span>
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent>
            <DropdownMenuRadioGroup value={chatModel} onValueChange={setChatModel}>
              <DropdownMenuRadioItem value="gpt-4">GPT-4</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="gpt-4-turbo">GPT-4 Turbo</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="gpt-3.5">GPT-3.5</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuSubContent>
        </DropdownMenuSub>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function CreateProjectDialog() {
  const [projectName, setProjectName] = React.useState("")
  const [selectedCategory, setSelectedCategory] = React.useState<string | null>(categories[0].id)
  const [memorySetting, setMemorySetting] = React.useState<"default" | "project-only">("default")
  const [selectedColor, setSelectedColor] = React.useState<string | null>("var(--foreground)")
  const [open, setOpen] = React.useState(false)

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon-sm">
          <HugeiconsIcon icon={PlusSignIcon} strokeWidth={2} />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <div className="flex items-center justify-between">
            <AlertDialogTitle>Create Project</AlertDialogTitle>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon-sm">
                  <HugeiconsIcon icon={Settings01Icon} strokeWidth={2} />
                  <span className="sr-only">Memory</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-72">
                <DropdownMenuRadioGroup
                  value={memorySetting}
                  onValueChange={(value) => {
                    setMemorySetting(value as "default" | "project-only")
                  }}
                >
                  <DropdownMenuRadioItem value="default">
                    <Item size="xs">
                      <ItemContent>
                        <ItemTitle>Default</ItemTitle>
                        <ItemDescription className="text-xs">
                          Project can access memories from outside chats, and vice versa.
                        </ItemDescription>
                      </ItemContent>
                    </Item>
                  </DropdownMenuRadioItem>
                  <DropdownMenuRadioItem value="project-only">
                    <Item size="xs">
                      <ItemContent>
                        <ItemTitle>Project Only</ItemTitle>
                        <ItemDescription className="text-xs">
                          Project can only access its own memories. Its memories are hidden from outside chats.
                        </ItemDescription>
                      </ItemContent>
                    </Item>
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
                <DropdownMenuSeparator />
                <DropdownMenuLabel>Note that this setting can&apos;t be changed later.</DropdownMenuLabel>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <AlertDialogDescription>
            Start a new project to keep chats, files, and custom instructions in one place.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="space-y-4">
          <Field>
            <FieldLabel htmlFor="project-name" className="sr-only">
              Project Name
            </FieldLabel>
            <InputGroup>
              <InputGroupInput
                id="project-name"
                placeholder="Copenhagen Trip"
                value={projectName}
                onChange={(e) => {
                  setProjectName(e.target.value)
                }}
              />
              <InputGroupAddon>
                <Popover>
                  <PopoverTrigger asChild>
                    <InputGroupButton variant="ghost" size="icon-xs">
                      <HugeiconsIcon
                        icon={FolderIcon}
                        strokeWidth={2}
                        style={{ "--color": selectedColor } as React.CSSProperties}
                        className="text-(--color)"
                      />
                    </InputGroupButton>
                  </PopoverTrigger>
                  <PopoverContent align="start" className="w-60 p-3">
                    <div className="flex flex-wrap gap-2">
                      {[
                        "var(--foreground)",
                        "#fa423e",
                        "#f59e0b",
                        "#8b5cf6",
                        "#ec4899",
                        "#10b981",
                        "#6366f1",
                        "#14b8a6",
                        "#f97316",
                        "#fbbc04",
                      ].map((color) => (
                        <Button
                          key={color}
                          size="icon"
                          variant="ghost"
                          className="rounded-full p-1"
                          style={{ "--color": color } as React.CSSProperties}
                          data-checked={selectedColor === color}
                          onClick={() => {
                            setSelectedColor(color)
                          }}
                        >
                          <span className="group-data-[checked=true]/button:ring-offset-background size-5 rounded-full bg-(--color) ring-2 ring-transparent ring-offset-2 ring-offset-(--color) group-data-[checked=true]/button:ring-(--color)" />
                          <span className="sr-only">{color}</span>
                        </Button>
                      ))}
                    </div>
                  </PopoverContent>
                </Popover>
              </InputGroupAddon>
            </InputGroup>
            <FieldDescription className="flex flex-wrap gap-2">
              {categories.map((category) => (
                <Badge
                  key={category.id}
                  variant={selectedCategory === category.id ? "default" : "outline"}
                  data-checked={selectedCategory === category.id}
                  asChild
                >
                  <button
                    onClick={() => {
                      setSelectedCategory(selectedCategory === category.id ? null : category.id)
                    }}
                  >
                    <HugeiconsIcon
                      icon={CheckmarkCircle02Icon}
                      strokeWidth={2}
                      data-icon="inline-start"
                      className="hidden group-data-[checked=true]/badge:inline"
                    />
                    {category.label}
                  </button>
                </Badge>
              ))}
            </FieldDescription>
          </Field>
          <Alert className="bg-muted">
            <HugeiconsIcon icon={BulbIcon} strokeWidth={2} />
            <AlertDescription className="text-xs">
              Projects keep chats, files, and custom instructions in one place. Use them for ongoing work, or just to
              keep things tidy.
            </AlertDescription>
          </Alert>
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={() => setOpen(false)}>Create project</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}

// Theme Toggle Component
function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  React.useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return null
  }

  const isDark = theme === "dark"

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={() => {
        const newTheme = isDark ? "light" : "dark"
        setTheme(newTheme)
      }}
      title={`Switch to ${isDark ? "light" : "dark"} mode`}
    >
      <HugeiconsIcon icon={isDark ? Sun03Icon : Moon02Icon} strokeWidth={2} />
    </Button>
  )
}

// Animation Toggle Component
function AnimationToggle({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
  return (
    <Button variant="ghost" size="icon-sm" onClick={onToggle} title={`Turn animations ${enabled ? "off" : "on"}`}>
      <HugeiconsIcon icon={SparklesIcon} strokeWidth={2} className={enabled ? "text-orange-500" : "opacity-50"} />
    </Button>
  )
}
