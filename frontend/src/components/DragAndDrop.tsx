// components/DragAndDrop.tsx
import React, { useRef, useState } from "react";

interface DragAndDropProps {
    onFileDrop: (event: React.ChangeEvent<HTMLInputElement>) => void;
    accept?: string;
    children?: React.ReactNode;
    className?: string;
    multiple?: boolean;
    maxSize?: number;
    fileTypeDescription?: string;
    fileTypeIcon?: string;
}

const DragAndDrop: React.FC<DragAndDropProps> = ({
    onFileDrop,
    accept = "*/*",
    children,
    className = "",
    multiple = false,
    maxSize,
    fileTypeDescription = "file",
    fileTypeIcon = "📁",
}) => {
    const [isDragging, setIsDragging] = useState(false);
    const [isDraggingOver, setIsDraggingOver] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const dragCounterRef = useRef(0);

    const handleDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
        setIsDraggingOver(true);
        setError(null);
        dragCounterRef.current += 1;
    };

    const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        setIsDraggingOver(false);
        dragCounterRef.current -= 1;
    };

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDraggingOver(true);
        if (!isDragging) {
            setIsDragging(true);
        }
    };

    const shortenFileName = (fileName: string) => {
        const parts = fileName.split('.');
        const ext = parts.pop();
        const name = parts.join('.');

        if (name.length > 20) {
            return name.slice(0, 10) + '***' + name.slice(-5) + '.' + ext;
        }
        return fileName;
    };

    const validateFiles = (files: FileList): boolean => {
        setError(null);

        // بررسی تعداد فایل‌ها
        if (!multiple && files.length > 1) {
            setError("Only 1 file is allowed.");
            return false;
        }

        // بررسی حجم فایل
        if (maxSize) {
            for (let i = 0; i < files.length; i++) {
                const fileSizeMB = files[i].size / (1024 * 1024);
                if (fileSizeMB > maxSize) {
                    setError(`The file size of ${shortenFileName(files[i].name)} exceeds ${maxSize}MB.`);
                    return false;
                }
            }
        }

        // بررسی نوع فایل (اگر accept مشخص شده باشد)
        if (accept !== "*/*") {
            const acceptedTypes = accept.split(",").map(type => type.trim());
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const isValid = acceptedTypes.some(type => {
                    if (type.startsWith(".")) {
                        // پسوند فایل
                        return file.name.toLowerCase().endsWith(type.toLowerCase());
                    } else if (type.includes("/")) {
                        // MIME type
                        return file.type.match(new RegExp(type.replace("*", ".*")));
                    }
                    return false;
                });

                if (!isValid) {
                    setError(`File type: ${file.name} is not supported.`);
                    return false;
                }
            }
        }

        return true;
    };

    const processFiles = (files: FileList) => {
        if (!validateFiles(files)) {
            return;
        }

        // Create a synthetic event to pass to onFileDrop
        const syntheticEvent = {
            target: {
                files: files,
            },
            currentTarget: {
                files: files,
            },
        } as unknown as React.ChangeEvent<HTMLInputElement>;

        onFileDrop(syntheticEvent);
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        setIsDraggingOver(false);
        dragCounterRef.current = 0;

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            processFiles(files);
        }
    };

    const handleClick = () => {
        setError(null);
        fileInputRef.current?.click();
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            processFiles(files);
        }
        // Reset the input so the same file can be uploaded again
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const getAcceptString = () => {
        if (accept === "*/*") return undefined;
        return accept;
    };

    return (
        <div
            className={`drag-and-drop ${className} ${isDragging ? "dragging" : ""} ${error ? "has-error" : ""}`}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={handleClick}
            role="button"
            tabIndex={0}
            aria-label={`Drop zone for ${fileTypeDescription}`}
        >
            <input
                ref={fileInputRef}
                type="file"
                accept={getAcceptString()}
                onChange={handleFileChange}
                multiple={multiple}
                style={{ display: "none" }}
                aria-hidden="true"
            />

            {error ? (
                <div className="drop-error">
                    <span>⚠️</span>
                    <p>{error}</p>
                    <small>Please try again.</small>
                </div>
            ) : (
                children || (
                    <div className="drop-content">
                        <span className="drop-icon">{isDraggingOver ? "📥" : fileTypeIcon}</span>
                        {isDraggingOver ? (
                            <p>Drop file here.</p>
                        ) : (
                            <p>Upload your {fileTypeDescription} file here.</p>
                        )}
                        {!isDraggingOver && <small>Or click here to choose a file.</small>}
                        {accept !== "*/*" && (
                            <span className="file-types">
                                {accept.split(",").join(" • ")}
                            </span>
                        )}
                        {maxSize && (
                            <span className="file-size-limit">
                                Maximum size: {maxSize}MB
                            </span>
                        )}
                        {multiple && (
                            <span className="multiple-files">📋 Multiple choises is allowed.</span>
                        )}
                    </div>
                )
            )}
        </div>
    );
};

export default DragAndDrop;