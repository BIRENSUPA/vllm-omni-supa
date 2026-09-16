#!/bin/bash

# -------------------------------------------------
# 壁仞软件栈组件构建脚本 build.sh
# 版本：1.0.0
# 功能：编译工程及测试用例代码, 打包、归档二进制制品产物。
### 用法: $0 [option]
### 示例：bash build.sh -a br100 -i -b Release -t regression
### Options:
###   -h       |  --help                        Print help.
###   -c       |  --clean                       Clean build dir. Only use in local build.
###   -i       |  --internal                    Internal package release.
###   -e       |  --external                    External package release.
###   -v       |  --verbose                     Print complete command. Only for dev.
###   -a <arg> |  --arch <arg>                  Supa gpu arch of BIREN device, build with br100 if not specified.
###   -b <arg> |  --build-type <arg>            <Debug|Release>.
###   -t <arg> |  --build-test <arg>            Enable build testing binary, regression used nightly test , and sanity used for MR CI test.
###   -j <arg> |  --jobs=<arg>                  Parallel compile jobs number.
###   --enable-coverage                         Enable code coverage.
###   --disable-ccache                          Disable ccache.
# ------------------------------------------------

# 严格错误退出
set -eo pipefail  

# -----------------
# 初始化默认变量配置
# -----------------
prefix="/usr/local" # Default path prefix to install header and lib
enable_build_test="false"
test_level="regression"
for_internal="false"
for_external="false"
parallel_jobs=16
build_type="Release"
supa_arch="br100"
enable_coverage=OFF
CUR_DIR="$( cd "$( dirname ${BASH_SOURCE[0]} )" >/dev/null 2>&1 && pwd )"
BUILD_DIR="${CUR_DIR}/build"
echo "[INFO] Current directory: ${CUR_DIR}"

# -----------------------
# 用户可配置变量（按需修改）
# -----------------------
# [begin customize] 二进制归档tar.gz包名,  如：suinfer.tar.gz；brcc.tar.gz（不含扩展名.tar.gz）
archive_name="suinfer" 
# [end customize]

# -------------
# CI流程传递变量
# -------------
# 构建编号：BUILD_ID, 本地开发环境默认为0
if [ -z ${BUILD_ID} ] || [ ${BUILD_ID} == "" ]; then
  export BUILD_ID="0"
fi

# -----------
# 脚本参数解析
# -----------
while [ $# -gt 0 ]; do
    case "${1}" in
    -h|--help)
        sed -rn 's/^### ?//;T;p;' "$0"
        exit 0
        ;;
    -c|--clean)
        rm -rf build dist *egg-info
        shift
        ;;
    -a|--arch)
      # 支持的supa GPU arch版本， 对应值会传给brcc编译器的--supa-gpu-arch参数选项
      export supa_arch=$2
      echo -e "[INFO] SUPA ARCH VERSION: $2"
      shift 2
      ;;
    -i|--internal)
      for_internal=true
      cmake_options=${cmake_options}" -DINTERNAL_BUILD=ON"
      shift
      ;;
    -e|--external)
      for_external=true
      cmake_options=${cmake_options}" -DEXTERNAL_BUILD=ON"
      shift
      ;;
    -t|--build-test)
      enable_build_test="true"
      test_level=$2
      cmake_options=${cmake_options}" -DBUILD_TEST=ON -DTEST_LEVEL=$2"
      shift 2
      ;;
    -b|--build-type)
      build_type=$2
      shift 2
      ;;
    --enable-coverage)
      enable_coverage=ON
      build_type=Debug
      shift
      ;;
    -j|--jobs)
      case "$2" in
        [1-9]|[1-9][0-9])
          parallel_jobs=$2
          shift 2
          ;;
        *)
          echo "1-99 for '$1', '$2' not supported.";
          exit 1
          ;;
      esac
      ;;
    --disable-ccache)
      export CCACHE_DISABLE=1
      shift
      ;;
    -v|--verbose)
      cmake_options=${cmake_options}" -DCMAKE_VERBOSE_MAKEFILE=ON"
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      echo -e "\033[31m[Failed]\033[0m Invalid input params!"
      echo -e "Please use 'build.sh -h' to print acceptable params"
      exit 1
      ;;
    esac
done

# -----------------
# 工具函数: 日志处理
# -----------------
log() {
  local level=$1
  local message=$2
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo -e "[${timestamp}] [${level}] ${message}"
}

# ---------------------------
# 工具函数: 获取操作系统统一名称
# ---------------------------
function get_os_from_os_release() {
    local os
    local os_id
    local os_version
    os_id=$(grep '^ID=' '/etc/os-release' | awk -F '=' '{print $2}' | tr -d '"')
    os_version=$(grep '^VERSION_ID=' '/etc/os-release' | awk -F '=' '{print $2}' | tr -d '"')
    os="${os_id}-${os_version}" 
    if [[ ${os} =~ rhel ]]; then
        os=$(echo "${os}" | sed 's/\(.*\)\..*/\1/') # 转换： rhel-7.x -> rhel-7, rhel-8.x -> rhel-8
    fi
    echo "${os}" # 如：ubuntu-20.04,ubuntu-22.04,ZTEOS-6.06,rhel-7
}

# ------------------------------------
# 构建步骤函数一： 安装三方依赖（按需修改）
# ------------------------------------
install_build_deps() {
  log "INFO" "安装${archive_name}编译时依赖的三方软件包..."
  # [begin customize] 根据实际需要选择是否额外安装
  local rpm_list="rpm_pkg_name1 rpm_pkg_name2 pkg_name3"
  local deb_list="deb_pkg_name1 deb_pkg_name2 deb_name3"
  local whl_pkg_list="whl_pkg_name1 whl_pkg_name2 whl_name3"
  os_id=$(grep '^ID=' '/etc/os-release' | awk -F '=' '{print $2}' | tr -d '"')
  case "${os_id}" in
    'ubuntu')
      # 类Debian/Ubuntu系统上安装编译依赖的三方包 -- 可选， 默认不需额外安装
      log "INFO" "安装${deb_list}..."
      sudo apt update
      # sudo apt-get install -y ${deb_list}
      ;;
    *)
      # 类Centos/Redhat系统上安装编译依赖的三方包 -- 可选， 默认不需额外安装
      log "INFO" "安装${rpm_list}..."
      # sudo yum install -y ${rpm_list}
      ;;
  esac
  
  # 安装编译依赖的三方python whl包 --可选， 默认不需额外安装
  log "INFO" "安装${whl_pkg_list}..."
  # python3 -m pip install ${whl_pkg_list} 

  # 指定特定操作系统安装三方包 -- 可选， 默认不需额外安装
  os=$(get_os_from_os_release)
  if [[ $os == "Replace_Actual_OS_Name" ]]; then
    log "INFO" "安装${archive_name}编译时依赖的三方软件包..."
    # sudo Replace_Actual_PKG_Tool install -y mesa-libGL-devel mesa-libGLU-devel  
  fi
  # [end customize]
}

# -----------------------
# 构建步骤函数二： 源码编译
# -----------------------
build() {
  log "INFO" "开始源码构建..."
  # [begin customize] define and add your needed macro 
  customized_cmake_options="-Dxxx=ON -Dyyy=OFF" # replace with all your needed macro
  # [end customize]
  cmake_options="-DBUILD_ID=${BUILD_ID} -DCMAKE_INSTALL_PREFIX=${prefix} -DCMAKE_BUILD_TYPE=${build_type} ${customized_cmake_options}"
  mkdir -p ${BUILD_DIR}
  cd ${BUILD_DIR}
  cmake_cmd="cmake ${cmake_options} .."
  eval "${cmake_cmd}" || {
    log "ERROR" "cmake命令执行失败"
    exit 1
  }
  make_cmd="make -j${parallel_jobs}"
  eval "${make_cmd}" || {
    log "ERROR" "make执行构建失败"
    exit 1
  }
  log "INFO" "源码构建成功!"
}

# -------------------------------------------
# 构建步骤函数三： 工程代码编译出的二进制内容打包
# -------------------------------------------
create_project_package() {
  log "INFO" "开始工程代码编译出的二进制内容打包..."
  cd ${BUILD_DIR}
  rm -rf ./tmp_for_tar/${archive_name}
  make install DESTDIR=./tmp_for_tar/${archive_name}
  cp -raf ./tmp_for_tar/${archive_name}${prefix}/* ./tmp_for_tar/${archive_name}/
  rm -rf ./tmp_for_tar/${archive_name}${prefix}
  cp -raf ../version.txt tmp_for_tar/${archive_name}
  cd tmp_for_tar && tar -czf ${archive_name}.tar.gz ${archive_name} && mv ${archive_name}.tar.gz ${BUILD_DIR} && cd -
  log "INFO" "工程代码编译出的二进制内容打包成功!"
}

# ----------------------------------
# 构建步骤函数四： 执行测试相关内容打包
# ----------------------------------
create_test_package() {
  log "INFO" "开始执行测试相关内容打包..."
  test_folder=${archive_name}-test
  test_archive_name=${test_folder}.tar.gz
  cd ${BUILD_DIR}
  rm -rf ${test_archive_name} ${archive_name}-test
  mkdir -p ${archive_name}-test
  # [begin customize] define own action by your actual value
  cp -raf test/xxx/test_file_1  \
          test/xxx/test_file_2  \
     ${test_folder}
  cp -raf ../.env_setup ${test_folder}
  # [End customize]
  tar -zcvf ${test_archive_name} ${test_folder}
  log "INFO" "执行测试相关内容打包成功!"
}

# ---------------------------
# 构建流程主函数
# ---------------------------
main() {
  # 安装三方依赖 - 非必选,  默认不需额外安装
  # install_build_deps
  build
  create_project_package
  if [ ${enable_build_test} = "true" ]; then
    create_test_package
  fi
  log "SUCCESS" "整体构建成功完成!"
}

# 执行入口，调用主函数
main
